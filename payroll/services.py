from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from attendance.models import AttendanceRecord
from hr.models import ApprovedLeave, Employee, Holiday
from hr.services import financial_year_bounds, get_working_dates, month_bounds
from payroll.models import PayrollEntry, PayrollRun


TWOPLACES = Decimal('0.01')


def quantize_money(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _approved_leave_dates(employee, start_date, end_date, holiday_dates):
    leave_dates = set()
    qs = ApprovedLeave.objects.filter(
        employee=employee,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    for approved_leave in qs:
        overlap_start = max(start_date, approved_leave.start_date)
        overlap_end = min(end_date, approved_leave.end_date)
        leave_dates.update(get_working_dates(overlap_start, overlap_end, holiday_dates))
    return leave_dates


def _attendance_dates(employee, start_date, end_date):
    return set(
        AttendanceRecord.objects.filter(
            employee=employee,
            attendance_date__range=(start_date, end_date),
        ).values_list('attendance_date', flat=True)
    )


def _employee_period_for_month(employee, payroll_month):
    month_start, month_end = month_bounds(payroll_month)
    if employee.join_date > month_end:
        return None, None
    period_start = max(employee.join_date, month_start)
    if employee.contract_end_date:
        if employee.contract_end_date < month_start:
            return None, None
        period_end = min(employee.contract_end_date, month_end)
    else:
        period_end = month_end
    return period_start, period_end


def calculate_payroll_for_employee(employee, payroll_month):
    month_start, month_end = month_bounds(payroll_month)
    period_start, period_end = _employee_period_for_month(employee, payroll_month)
    if not period_start or not period_end:
        return None

    holiday_dates = set(Holiday.objects.filter(date__range=(period_start, period_end)).values_list('date', flat=True))
    working_dates = set(get_working_dates(period_start, period_end, holiday_dates))
    attendance_dates = _attendance_dates(employee, period_start, period_end)
    approved_leave_dates = _approved_leave_dates(employee, period_start, period_end, holiday_dates)
    approved_absence_dates = approved_leave_dates - attendance_dates

    if employee.included_in_attendance:
        unapproved_absence_dates = working_dates - attendance_dates - approved_leave_dates
        present_days = len(working_dates.intersection(attendance_dates))
    else:
        unapproved_absence_dates = set()
        present_days = 0

    fy_start, _ = financial_year_bounds(month_start)
    prior_end = month_start - timedelta(days=1)
    prior_start = max(fy_start, employee.join_date)
    prior_approved_count = 0
    if prior_start <= prior_end:
        if employee.contract_end_date and employee.contract_end_date < prior_start:
            prior_approved_count = 0
        else:
            prior_period_end = min(prior_end, employee.contract_end_date or prior_end)
            prior_holidays = set(Holiday.objects.filter(date__range=(prior_start, prior_period_end)).values_list('date', flat=True))
            prior_approved_dates = _approved_leave_dates(employee, prior_start, prior_period_end, prior_holidays)
            prior_attendance_dates = _attendance_dates(employee, prior_start, prior_period_end)
            prior_approved_count = len(prior_approved_dates - prior_attendance_dates)

    annual_remaining = max(employee.annual_leave_allowance - prior_approved_count, 0)
    approved_leave_days = len(approved_absence_dates)
    approved_paid_leave_days = min(approved_leave_days, employee.monthly_leave_cap, annual_remaining)
    approved_lwp_days = max(approved_leave_days - approved_paid_leave_days, 0)
    unapproved_lwp_days = len(unapproved_absence_dates)
    total_lwp_days = approved_lwp_days + unapproved_lwp_days

    total_calendar_days = month_end.day
    active_calendar_days = (period_end - period_start).days + 1
    monthly_compensation = Decimal(employee.monthly_compensation)
    per_day_deduction = monthly_compensation / Decimal(total_calendar_days)
    gross_payable = monthly_compensation * Decimal(active_calendar_days) / Decimal(total_calendar_days)
    net_payable = gross_payable - (per_day_deduction * Decimal(total_lwp_days))
    if net_payable < 0:
        net_payable = Decimal('0.00')

    return {
        'full_name': employee.full_name,
        'work_email': employee.work_email,
        'employment_type': employee.get_employment_type_display(),
        'department': employee.department,
        'designation': employee.designation,
        'date_of_joining': employee.join_date,
        'contract_end_date': employee.contract_end_date,
        'annual_leave_allowance': employee.annual_leave_allowance,
        'annual_leave_used_before_month': prior_approved_count,
        'monthly_leave_cap': employee.monthly_leave_cap,
        'total_calendar_days': total_calendar_days,
        'active_calendar_days': active_calendar_days,
        'working_days': len(working_dates),
        'holidays_in_month': len(holiday_dates),
        'present_days': present_days,
        'approved_leave_days': approved_leave_days,
        'approved_paid_leave_days': approved_paid_leave_days,
        'approved_lwp_days': approved_lwp_days,
        'unapproved_lwp_days': unapproved_lwp_days,
        'total_lwp_days': total_lwp_days,
        'monthly_compensation': quantize_money(monthly_compensation),
        'per_day_deduction': quantize_money(per_day_deduction),
        'gross_payable': quantize_money(gross_payable),
        'net_payable': quantize_money(net_payable),
    }


def generate_payroll_run(payroll_month, user):
    month_start, month_end = month_bounds(payroll_month)
    today = timezone.localdate()
    if today <= month_end:
        raise ValidationError('Payroll can only be generated after the selected month has completed.')

    employees = Employee.objects.filter(
        is_active=True,
        join_date__lte=month_end,
    ).exclude(contract_end_date__lt=month_start)

    with transaction.atomic():
        run, created = PayrollRun.objects.get_or_create(
            payroll_month=month_start,
            defaults={'generated_by': user, 'generated_at': timezone.now()},
        )
        if not created:
            run.entries.all().delete()
            run.generated_by = user
            run.generated_at = timezone.now()
            run.save(update_fields=['generated_by', 'generated_at'])

        entries = []
        for employee in employees:
            payload = calculate_payroll_for_employee(employee, month_start)
            if not payload:
                continue
            entries.append(PayrollEntry(run=run, employee=employee, **payload))

        PayrollEntry.objects.bulk_create(entries)

    return run
