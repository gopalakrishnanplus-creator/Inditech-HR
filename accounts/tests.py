from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from hr.models import Employee


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
