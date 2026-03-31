from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from attendance.models import AttendanceRecord
from hr.models import Employee, Holiday

from .models import RoleAssignment


class AttendanceEntryViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='employee@example.com',
            email='employee@example.com',
            password='password123',
        )

    def test_employee_is_redirected_to_attendance_submit(self):
        Employee.objects.create(
            full_name='Employee User',
            work_email='employee@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            designation='Executive',
            monthly_compensation='25000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2026-01-01',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('accounts:attendance-entry'))

        self.assertRedirects(response, reverse('attendance:submit'))

    def test_non_employee_is_redirected_to_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('accounts:attendance-entry'))

        self.assertRedirects(response, reverse('accounts:dashboard'))


class AttendanceLoginViewTests(TestCase):
    def test_authenticated_user_is_redirected_to_attendance_entry(self):
        user = get_user_model().objects.create_user(
            username='signedin@example.com',
            email='signedin@example.com',
            password='password123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:attendance-login'))

        self.assertRedirects(
            response,
            reverse('accounts:attendance-entry'),
            fetch_redirect_response=False,
        )


class HRManagerAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='hr.manager@example.com',
            email='hr.manager@example.com',
            password='password123',
        )
        RoleAssignment.objects.create(
            email='hr.manager@example.com',
            display_name='HR Manager',
            role=RoleAssignment.Role.HR_MANAGER,
        )
        self.client.force_login(self.user)

    def test_hr_manager_dashboard_includes_payroll_and_leave_links(self):
        response = self.client.get(reverse('accounts:dashboard'))

        self.assertContains(response, 'Payroll')
        self.assertContains(response, 'Approved Leaves')
        self.assertContains(response, 'Holidays')

    def test_hr_manager_can_open_payroll_run_list(self):
        response = self.client.get(reverse('payroll:run-list'))

        self.assertEqual(response.status_code, 200)

    @patch('accounts.views.timezone.localdate', return_value=date(2026, 3, 31))
    def test_hr_manager_can_open_upcoming_contracts_list(self, mocked_today):
        Employee.objects.create(
            full_name='Contract Ending Soon',
            work_email='soon@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            designation='Associate',
            monthly_compensation='28000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2025-01-01',
            contract_end_date=date(2026, 4, 15),
        )

        response = self.client.get(reverse('accounts:upcoming-contracts'))

        self.assertContains(response, 'Contract Ending Soon')
        self.assertContains(response, 'April 15, 2026')

    @patch('accounts.views.timezone.localdate', return_value=date(2026, 3, 31))
    def test_attendance_summary_shows_current_month_and_absent_days_link(self, mocked_today):
        employee = Employee.objects.create(
            full_name='Attendance Person',
            work_email='attendance.person@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            designation='Executive',
            monthly_compensation='30000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2026-03-01',
        )
        Holiday.objects.create(name='Festival Holiday', date=date(2026, 3, 10))
        AttendanceRecord.objects.create(
            employee=employee,
            attendance_date=date(2026, 3, 1),
            employee_name=employee.full_name,
            employment_type=employee.employment_type,
            reports_to_name='',
            work_summary='Worked on tasks.',
        )
        AttendanceRecord.objects.create(
            employee=employee,
            attendance_date=date(2026, 3, 2),
            employee_name=employee.full_name,
            employment_type=employee.employment_type,
            reports_to_name='',
            work_summary='Worked on tasks.',
        )

        response = self.client.get(reverse('accounts:attendance-summary'))

        self.assertContains(response, 'Attendance Summary')
        self.assertContains(response, 'Attendance Person')
        self.assertContains(response, 'Number of Absent Days')
        self.assertContains(response, 'Previous Month')
        self.assertContains(response, reverse('accounts:attendance-missing-dates', kwargs={'pk': employee.pk}))


class AttendanceNavigationTests(TestCase):
    def test_attendance_pages_hide_management_buttons_for_mixed_role_user(self):
        user = get_user_model().objects.create_user(
            username='mixed.role@example.com',
            email='mixed.role@example.com',
            password='password123',
        )
        RoleAssignment.objects.create(
            email='mixed.role@example.com',
            display_name='Mixed Role',
            role=RoleAssignment.Role.HR_MANAGER,
        )
        Employee.objects.create(
            full_name='Mixed Role User',
            work_email='mixed.role@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            designation='Lead',
            monthly_compensation='40000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2026-01-01',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('attendance:submit'))

        self.assertNotContains(response, 'Employees')
        self.assertNotContains(response, 'Contracts')
        self.assertNotContains(response, 'Payroll')
        self.assertNotContains(response, 'Approved Leaves')
        self.assertContains(response, 'Submit Attendance')
