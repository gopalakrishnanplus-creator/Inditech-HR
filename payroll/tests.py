from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from attendance.models import AttendanceRecord
from hr.models import ApprovedLeave, Employee
from hr.services import get_working_dates

from .services import calculate_payroll_for_employee, generate_payroll_run


class PayrollServiceTests(TestCase):
    def setUp(self):
        self.finance_user = get_user_model().objects.create_user(
            username='finance@example.com',
            email='finance@example.com',
            password='password123',
        )
        self.employee = Employee.objects.create(
            full_name='Payroll Person',
            work_email='payroll@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Finance',
            designation='Analyst',
            monthly_compensation='31000.00',
            annual_leave_allowance=1,
            monthly_leave_cap=1,
            join_date=date(2024, 1, 1),
        )

    def test_payroll_calculation_counts_lwp_correctly(self):
        payroll_month = date(2024, 3, 1)
        working_dates = get_working_dates(date(2024, 3, 1), date(2024, 3, 31), set())
        approved_leave_dates = {date(2024, 3, 4), date(2024, 3, 5)}
        unapproved_absence = date(2024, 3, 6)

        for working_date in working_dates:
            if working_date in approved_leave_dates or working_date == unapproved_absence:
                continue
            AttendanceRecord.objects.create(
                employee=self.employee,
                attendance_date=working_date,
                employee_name=self.employee.full_name,
                employment_type=self.employee.employment_type,
                reports_to_name='',
                work_summary='Worked',
            )

        ApprovedLeave.objects.create(
            employee=self.employee,
            start_date=date(2024, 3, 4),
            end_date=date(2024, 3, 5),
            approved_by=self.finance_user,
        )

        result = calculate_payroll_for_employee(self.employee, payroll_month)

        self.assertEqual(result['approved_leave_days'], 2)
        self.assertEqual(result['approved_paid_leave_days'], 1)
        self.assertEqual(result['approved_lwp_days'], 1)
        self.assertEqual(result['unapproved_lwp_days'], 1)
        self.assertEqual(result['total_lwp_days'], 2)
        self.assertEqual(result['net_payable'], Decimal('29000.00'))

    def test_generate_payroll_requires_completed_month(self):
        with patch('payroll.services.timezone.localdate', return_value=date(2026, 3, 21)):
            with self.assertRaises(ValidationError):
                generate_payroll_run(date(2026, 3, 1), self.finance_user)

# Create your tests here.
