from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import RoleAssignment
from attendance.models import AttendanceRecord
from hr.models import ApprovedLeave, Employee
from hr.services import get_working_dates

from .models import ManagerPayrollApproval
from .services import calculate_payroll_for_employee, generate_payroll_run, send_manager_payroll_approval_requests


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
            manager_name='Manager One',
            manager_email='manager.one@example.com',
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

    def test_generate_previous_month_payroll_requires_manager_approval(self):
        with patch('payroll.services.timezone.localdate', return_value=date(2026, 4, 10)):
            with self.assertRaises(ValidationError) as exc:
                generate_payroll_run(date(2026, 3, 1), self.finance_user)

        self.assertIn('Manager payroll approvals are still pending', str(exc.exception))

    def test_generate_previous_month_payroll_succeeds_after_manager_approval(self):
        ManagerPayrollApproval.objects.create(
            payroll_month=date(2026, 3, 1),
            manager_name='Manager One',
            manager_email='manager.one@example.com',
            approved_by=self.finance_user,
            approved_at='2026-04-02T10:00:00+05:30',
        )

        with patch('payroll.services.timezone.localdate', return_value=date(2026, 4, 10)):
            run = generate_payroll_run(date(2026, 3, 1), self.finance_user)

        self.assertEqual(run.payroll_month, date(2026, 3, 1))

    @patch('payroll.services.send_manager_payroll_approval_email')
    def test_manager_approval_emails_do_not_start_before_may_2026(self, mocked_send):
        sent_count = send_manager_payroll_approval_requests(reference_date=date(2026, 4, 1))

        self.assertEqual(sent_count, 0)
        mocked_send.assert_not_called()

    @patch('payroll.services.send_manager_payroll_approval_email')
    def test_manager_approval_emails_send_from_may_2026(self, mocked_send):
        RoleAssignment.objects.create(
            email='hr.manager@example.com',
            display_name='HR Manager',
            role=RoleAssignment.Role.HR_MANAGER,
        )

        sent_count = send_manager_payroll_approval_requests(reference_date=date(2026, 5, 1))

        self.assertEqual(sent_count, 1)
        approval = ManagerPayrollApproval.objects.get(payroll_month=date(2026, 4, 1), manager_email='manager.one@example.com')
        self.assertEqual(approval.manager_name, 'Manager One')
        self.assertIsNotNone(approval.notification_sent_at)
        mocked_send.assert_called_once_with('Manager One', 'manager.one@example.com', date(2026, 4, 1))


class ManagerPayrollApprovalViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='manager.one@example.com',
            email='manager.one@example.com',
            password='password123',
        )
        self.employee = Employee.objects.create(
            full_name='Reportee One',
            work_email='reportee.one@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            manager_name='Manager One',
            manager_email='manager.one@example.com',
            designation='Analyst',
            monthly_compensation='31000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date=date(2026, 4, 1),
        )

    def test_manager_approval_link_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('payroll:manager-approval'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:landing'), response.url)

    def test_manager_approval_page_renders_for_authorized_manager(self):
        self.client.force_login(self.user)

        with patch('payroll.views.timezone.localdate', return_value=date(2026, 5, 1)):
            response = self.client.get(reverse('payroll:manager-approval'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manager Payroll Approval')
        self.assertContains(response, self.employee.full_name)

# Create your tests here.
