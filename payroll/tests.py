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
from .services import (
    calculate_payroll_for_employee,
    generate_payroll_run,
    get_manager_approval_dashboard_link,
    get_manager_approval_groups,
    send_manager_payroll_approval_requests,
)


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

    def test_manager_approval_link_includes_target_manager_email(self):
        link = get_manager_approval_dashboard_link(manager_email='Manager.One@Example.com')

        self.assertIn('/payroll/manager-approval/', link)
        self.assertIn('manager_email=manager.one%40example.com', link)

    def test_recently_inactive_employee_with_month_overlap_is_included_in_manager_approval(self):
        inactive_employee = Employee.objects.create(
            full_name='Recently Inactive',
            work_email='inactive@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Finance',
            manager_name='Manager One',
            manager_email='manager.one@example.com',
            designation='Analyst',
            monthly_compensation='25000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date=date(2026, 1, 1),
            contract_end_date=date(2026, 4, 20),
            is_active=False,
        )

        groups = get_manager_approval_groups(date(2026, 4, 1))
        manager_group = next(group for group in groups if group['manager_email'] == 'manager.one@example.com')
        group_employee_names = {row['employee'].full_name for row in manager_group['rows']}

        self.assertIn(inactive_employee.full_name, group_employee_names)


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
        self.assertContains(response, 'Expected for full month')

    def test_manager_only_user_is_redirected_away_from_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('accounts:dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('payroll:manager-approval'))

    def test_manager_only_user_is_redirected_away_from_holiday_list(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('hr:holiday-list'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('payroll:manager-approval'))

    def test_manager_approval_page_shows_email_mismatch_message(self):
        other_user, _ = get_user_model().objects.get_or_create(
            username='gopala.krishnan@inditech.co.in',
            defaults={'email': 'gopala.krishnan@inditech.co.in'},
        )
        self.client.force_login(other_user)

        with patch('payroll.views.timezone.localdate', return_value=date(2026, 5, 1)):
            response = self.client.get(
                f"{reverse('payroll:manager-approval')}?manager_email=manager.one@example.com"
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This approval request was sent to')
        self.assertContains(response, 'manager.one@example.com')
        self.assertContains(response, 'gopala.krishnan@inditech.co.in')

    def test_manager_approval_page_shows_partial_month_availability_for_ended_contract(self):
        self.client.force_login(self.user)
        self.employee.contract_end_date = date(2026, 4, 17)
        self.employee.save(update_fields=['contract_end_date'])

        with patch('payroll.views.timezone.localdate', return_value=date(2026, 5, 1)):
            response = self.client.get(reverse('payroll:manager-approval'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Expected through Apr 17')
        self.assertContains(response, 'Apr 1 to Apr 17')

# Create your tests here.
