from datetime import timedelta

from django.utils import timezone

from accounts.emailing import send_sendgrid_email
from hr.models import Employee, Holiday
from hr.services import is_working_day

from .models import AttendanceRecord


ATTENDANCE_REMINDER_SUBJECT = 'You have not submitted attendance for yesterday'
ATTENDANCE_REMINDER_BODY = (
    'You have not submitted attendance for yesterday. '
    'You can ignore this email if you have taken leave yesterday with email/written approval from your manager. '
    'If not, please talk to your manager, as it will be considered leave without pay as per company HR policy.'
)


def get_attendance_reminder_target_date(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    target_date = reference_date - timedelta(days=1)
    holiday_dates = set(Holiday.objects.filter(date=target_date).values_list('date', flat=True))
    if not is_working_day(target_date, holiday_dates):
        return None
    return target_date


def get_missing_attendance_employees(target_date):
    employees = Employee.objects.filter(
        is_active=True,
        included_in_attendance=True,
        join_date__lte=target_date,
    ).exclude(contract_end_date__lt=target_date)
    submitted_employee_ids = set(
        AttendanceRecord.objects.filter(attendance_date=target_date).values_list('employee_id', flat=True)
    )
    return employees.exclude(pk__in=submitted_employee_ids).order_by('full_name')


def send_attendance_reminder_email(employee):
    send_sendgrid_email(
        employee.work_email,
        ATTENDANCE_REMINDER_SUBJECT,
        ATTENDANCE_REMINDER_BODY,
    )


def send_daily_attendance_reminders(reference_date=None):
    target_date = get_attendance_reminder_target_date(reference_date=reference_date)
    if not target_date:
        return 0

    sent_count = 0
    for employee in get_missing_attendance_employees(target_date):
        send_attendance_reminder_email(employee)
        sent_count += 1
    return sent_count
