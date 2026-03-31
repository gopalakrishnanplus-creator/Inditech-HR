from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from hr.models import Employee

from .models import AttendanceRecord


class AttendanceSubmissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='person@example.com',
            email='person@example.com',
            password='password123',
        )
        self.employee = Employee.objects.create(
            full_name='Test Person',
            work_email='person@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            manager_name='External Manager',
            manager_email='external.manager@example.com',
            designation='Coordinator',
            monthly_compensation='30000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2024-01-01',
        )
        self.client.force_login(self.user)

    def test_employee_can_submit_attendance_once_per_day(self):
        response = self.client.post(
            reverse('attendance:submit'),
            {'work_summary': 'Completed assigned work.'},
        )
        self.assertRedirects(response, reverse('attendance:submit'))
        self.assertEqual(AttendanceRecord.objects.count(), 1)

        duplicate_response = self.client.post(
            reverse('attendance:submit'),
            {'work_summary': 'Attempting a second submission.'},
        )
        self.assertRedirects(duplicate_response, reverse('attendance:submit'))
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        record = AttendanceRecord.objects.get()
        self.assertEqual(record.attendance_date, timezone.localdate())
        self.assertEqual(record.employee_name, 'Test Person')
        self.assertEqual(record.reports_to_name, 'External Manager')

# Create your tests here.
