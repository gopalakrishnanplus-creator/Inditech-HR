import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from hr.models import Employee
from payroll.services import (
    get_employee_monthly_approval_snapshot,
    get_manager_approval_groups,
    get_payroll_employees_for_month,
)


class Command(BaseCommand):
    help = 'Debug manager approval grouping for a manager and optional reportee name.'

    def add_arguments(self, parser):
        parser.add_argument('--manager-name', required=True)
        parser.add_argument('--employee-name')
        parser.add_argument('--month', required=True, help='Payroll month in YYYY-MM format.')

    def handle(self, *args, **options):
        try:
            year, month = [int(part) for part in options['month'].split('-')]
            payroll_month = date(year, month, 1)
        except ValueError as exc:
            raise CommandError('--month must be in YYYY-MM format.') from exc

        manager_name = options['manager_name']
        employee_name = options.get('employee_name') or ''
        payroll_employee_ids = set(
            get_payroll_employees_for_month(payroll_month).values_list('id', flat=True)
        )
        manager_matches = Employee.objects.filter(manager_name__icontains=manager_name).order_by('full_name')
        employee_matches = (
            Employee.objects.filter(full_name__icontains=employee_name).order_by('full_name')
            if employee_name
            else Employee.objects.none()
        )
        groups = get_manager_approval_groups(payroll_month)

        payload = {
            'payroll_month': payroll_month.isoformat(),
            'manager_name_query': manager_name,
            'employee_name_query': employee_name,
            'manager_matches': [self.serialize_employee(employee, payroll_month, payroll_employee_ids) for employee in manager_matches],
            'employee_matches': [self.serialize_employee(employee, payroll_month, payroll_employee_ids) for employee in employee_matches],
            'groups_matching_manager_name': [
                {
                    'manager_name': group['manager_name'],
                    'manager_email': group['manager_email'],
                    'row_count': len(group['rows']),
                    'row_names': [row['employee'].full_name for row in group['rows']],
                }
                for group in groups
                if manager_name.lower() in group['manager_name'].lower()
            ],
        }
        self.stdout.write(json.dumps(payload, indent=2, default=str))

    def serialize_employee(self, employee, payroll_month, payroll_employee_ids):
        snapshot = get_employee_monthly_approval_snapshot(employee, payroll_month)
        return {
            'id': employee.id,
            'full_name': employee.full_name,
            'work_email': employee.work_email,
            'manager_name': employee.manager_name,
            'manager_email': employee.manager_email,
            'join_date': employee.join_date,
            'contract_end_date': employee.contract_end_date,
            'included_in_payroll_month_queryset': employee.id in payroll_employee_ids,
            'snapshot_exists': snapshot is not None,
            'snapshot_period_start': snapshot['period_start'] if snapshot else None,
            'snapshot_period_end': snapshot['period_end'] if snapshot else None,
            'snapshot_days_without_attendance': snapshot['days_without_attendance'] if snapshot else None,
            'snapshot_approved_non_attendance_days': snapshot['approved_non_attendance_days'] if snapshot else None,
        }
