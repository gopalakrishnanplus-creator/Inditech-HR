import os
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode, urljoin

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.emailing import send_sendgrid_email
from accounts.services import normalize_email
from attendance.models import AttendanceRecord
from hr.models import ApprovedLeave, Employee, Holiday
from hr.services import financial_year_bounds, get_working_dates, month_bounds
from payroll.models import ManagerPayrollApproval, PayrollEntry, PayrollRun


TWOPLACES = Decimal('0.01')
MANAGER_APPROVAL_EMAIL_START_DATE = date(2026, 5, 1)


def quantize_money(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def get_previous_month_start(reference_date):
    return (reference_date.replace(day=1) - timedelta(days=1)).replace(day=1)


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


def _effective_attendance_dates(attendance_dates, approved_leave_dates):
    return attendance_dates - approved_leave_dates


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


def get_payroll_employees_for_month(payroll_month):
    month_start, month_end = month_bounds(payroll_month)
    return Employee.objects.filter(
        join_date__lte=month_end,
    ).exclude(contract_end_date__lt=month_start)


def get_manager_group_key(employee):
    manager_email = normalize_email(employee.manager_email)
    manager_name = (employee.manager_name or '').strip()
    if manager_email:
        return manager_email, manager_name or manager_email
    return '', manager_name or 'Manager not configured'


def get_employee_monthly_approval_snapshot(employee, payroll_month):
    month_start, month_end = month_bounds(payroll_month)
    period_start, period_end = _employee_period_for_month(employee, payroll_month)
    if not period_start or not period_end:
        return None

    holiday_dates = set(Holiday.objects.filter(date__range=(period_start, period_end)).values_list('date', flat=True))
    working_dates = set(get_working_dates(period_start, period_end, holiday_dates))
    attendance_dates = _attendance_dates(employee, period_start, period_end)
    approved_leave_dates = _approved_leave_dates(employee, period_start, period_end, holiday_dates)
    effective_attendance_dates = _effective_attendance_dates(attendance_dates, approved_leave_dates)

    if employee.included_in_attendance:
        days_without_attendance = working_dates - effective_attendance_dates
        unapproved_absence_dates = days_without_attendance - approved_leave_dates
    else:
        days_without_attendance = set()
        unapproved_absence_dates = set()

    return {
        'employee': employee,
        'approved_leave_days': len(approved_leave_dates),
        'days_without_attendance': len(days_without_attendance),
        'unapproved_absent_days': len(unapproved_absence_dates),
        'period_start': period_start,
        'period_end': period_end,
        'month_start': month_start,
        'month_end': month_end,
        'employment_status': employee.status_label_on(period_end),
        'expected_availability_label': (
            f'Expected through {period_end.strftime("%b")} {period_end.day}'
            if period_end < month_end
            else 'Expected for full month'
        ),
    }


def get_manager_approval_groups(payroll_month):
    approval_by_email = {
        approval.manager_email: approval
        for approval in ManagerPayrollApproval.objects.filter(payroll_month=payroll_month)
    }
    grouped_rows = defaultdict(list)
    manager_names = {}
    employees_without_manager = []

    for employee in get_payroll_employees_for_month(payroll_month).order_by('full_name'):
        snapshot = get_employee_monthly_approval_snapshot(employee, payroll_month)
        if not snapshot:
            continue

        manager_email, manager_name = get_manager_group_key(employee)
        if not manager_email:
            employees_without_manager.append(snapshot)
            continue

        grouped_rows[manager_email].append(snapshot)
        manager_names[manager_email] = manager_name

    groups = []
    for manager_email in sorted(grouped_rows):
        groups.append(
            {
                'manager_email': manager_email,
                'manager_name': manager_names.get(manager_email, manager_email),
                'rows': grouped_rows[manager_email],
                'approval': approval_by_email.get(manager_email),
            }
        )

    if employees_without_manager:
        groups.append(
            {
                'manager_email': '',
                'manager_name': 'Manager not configured',
                'rows': employees_without_manager,
                'approval': None,
            }
        )

    return groups


def get_manager_group_for_email(manager_email, payroll_month):
    manager_email = normalize_email(manager_email)
    for group in get_manager_approval_groups(payroll_month):
        if normalize_email(group['manager_email']) == manager_email:
            return group
    return None


def validate_manager_approvals_for_month(payroll_month):
    pending_groups = []
    missing_manager_rows = []
    for group in get_manager_approval_groups(payroll_month):
        if not group['manager_email']:
            missing_manager_rows.extend(group['rows'])
            continue
        if not group['approval'] or not group['approval'].approved_at:
            pending_groups.append(group)

    if missing_manager_rows:
        employee_names = ', '.join(row['employee'].full_name for row in missing_manager_rows[:5])
        if len(missing_manager_rows) > 5:
            employee_names += ', ...'
        raise ValidationError(f'Manager details are missing for: {employee_names}.')

    if pending_groups:
        manager_names = ', '.join(group['manager_name'] for group in pending_groups[:5])
        if len(pending_groups) > 5:
            manager_names += ', ...'
        raise ValidationError(f'Manager payroll approvals are still pending from: {manager_names}.')


def get_previous_month_label(reference_date):
    previous_month = get_previous_month_start(reference_date)
    return previous_month.strftime('%B'), previous_month.year


def get_manager_approval_dashboard_link(manager_email=None):
    base_url = os.environ.get('APP_BASE_URL', 'http://127.0.0.1:8000').rstrip('/') + '/'
    url = urljoin(base_url, 'payroll/manager-approval/')
    if manager_email:
        return f'{url}?{urlencode({"manager_email": normalize_email(manager_email)})}'
    return url


def send_manager_payroll_approval_email(manager_name, manager_email, payroll_month):
    month_name = payroll_month.strftime('%B')
    subject = f"Approve payroll for {manager_name}'s reportees. {month_name}, {payroll_month.year}"
    body = (
        "Approve the payroll for your reportees at this link - "
        f"{get_manager_approval_dashboard_link(manager_email=manager_email)}"
    )
    send_sendgrid_email(manager_email, subject, body)


def send_manager_payroll_approval_requests(reference_date=None, force=False):
    reference_date = reference_date or timezone.localdate()
    if reference_date < MANAGER_APPROVAL_EMAIL_START_DATE and not force:
        return 0
    if reference_date.day != 1 and not force:
        return 0

    payroll_month = get_previous_month_start(reference_date)
    sent_count = 0
    for group in get_manager_approval_groups(payroll_month):
        if not group['manager_email']:
            continue

        approval, _ = ManagerPayrollApproval.objects.get_or_create(
            payroll_month=payroll_month,
            manager_email=group['manager_email'],
            defaults={'manager_name': group['manager_name']},
        )
        if approval.notification_sent_at and not force:
            continue

        approval.manager_name = group['manager_name']
        send_manager_payroll_approval_email(group['manager_name'], group['manager_email'], payroll_month)
        approval.notification_sent_at = timezone.now()
        approval.save(update_fields=['manager_name', 'notification_sent_at', 'updated_at'])
        sent_count += 1

    return sent_count


def calculate_payroll_for_employee(employee, payroll_month):
    month_start, month_end = month_bounds(payroll_month)
    period_start, period_end = _employee_period_for_month(employee, payroll_month)
    if not period_start or not period_end:
        return None

    holiday_dates = set(Holiday.objects.filter(date__range=(period_start, period_end)).values_list('date', flat=True))
    working_dates = set(get_working_dates(period_start, period_end, holiday_dates))
    attendance_dates = _attendance_dates(employee, period_start, period_end)
    approved_leave_dates = _approved_leave_dates(employee, period_start, period_end, holiday_dates)
    effective_attendance_dates = _effective_attendance_dates(attendance_dates, approved_leave_dates)

    if employee.included_in_attendance:
        unapproved_absence_dates = working_dates - effective_attendance_dates - approved_leave_dates
        present_days = len(working_dates.intersection(effective_attendance_dates))
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
            prior_approved_count = len(prior_approved_dates)

    annual_remaining = max(employee.annual_leave_allowance - prior_approved_count, 0)
    approved_leave_days = len(approved_leave_dates)
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

    if month_start == get_previous_month_start(today):
        validate_manager_approvals_for_month(month_start)

    employees = get_payroll_employees_for_month(month_start)

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
