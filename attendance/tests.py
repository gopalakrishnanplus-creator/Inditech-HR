from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from hr.models import ApprovedLeave, Employee, Holiday

from .models import AttendanceRecord
from .services import send_daily_attendance_reminders


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

    def test_employee_cannot_submit_attendance_on_approved_leave_day(self):
        ApprovedLeave.objects.create(
            employee=self.employee,
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            notes='Approved leave',
        )

        response = self.client.post(
            reverse('attendance:submit'),
            {'work_summary': 'Attempted submission on approved leave.'},
            follow=True,
        )

        self.assertEqual(AttendanceRecord.objects.count(), 0)
        self.assertContains(response, 'You cannot fill in attendance for today because you are on approved leave.')


class AttendanceReminderTests(TestCase):
    def setUp(self):
        self.employee_missing = Employee.objects.create(
            full_name='Missing Attendance',
            work_email='missing@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            manager_name='Manager',
            manager_email='manager@example.com',
            designation='Executive',
            monthly_compensation='25000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2026-03-01',
        )
        self.employee_submitted = Employee.objects.create(
            full_name='Submitted Attendance',
            work_email='submitted@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            manager_name='Manager',
            manager_email='manager@example.com',
            designation='Executive',
            monthly_compensation='25000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2026-03-01',
        )

    @patch('attendance.services.send_attendance_reminder_email')
    def test_daily_reminders_send_only_for_missing_previous_working_day(self, mocked_send):
        AttendanceRecord.objects.create(
            employee=self.employee_submitted,
            attendance_date=date(2026, 4, 1),
            employee_name=self.employee_submitted.full_name,
            employment_type=self.employee_submitted.employment_type,
            reports_to_name=self.employee_submitted.manager_name,
            work_summary='Worked',
        )

        sent_count = send_daily_attendance_reminders(reference_date=date(2026, 4, 2))

        self.assertEqual(sent_count, 1)
        mocked_send.assert_called_once_with(self.employee_missing)

    @patch('attendance.services.send_attendance_reminder_email')
    def test_daily_reminders_skip_non_working_previous_day(self, mocked_send):
        Holiday.objects.create(name='Company Holiday', date=date(2026, 4, 2))

        sent_count = send_daily_attendance_reminders(reference_date=date(2026, 4, 3))

        self.assertEqual(sent_count, 0)
        mocked_send.assert_not_called()

    @patch('attendance.services.send_attendance_reminder_email')
    def test_daily_reminders_include_employee_active_on_target_date_even_if_currently_inactive(self, mocked_send):
        AttendanceRecord.objects.create(
            employee=self.employee_submitted,
            attendance_date=date(2026, 4, 1),
            employee_name=self.employee_submitted.full_name,
            employment_type=self.employee_submitted.employment_type,
            reports_to_name=self.employee_submitted.manager_name,
            work_summary='Worked',
        )
        recently_inactive = Employee.objects.create(
            full_name='Recently Inactive',
            work_email='recently.inactive@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Operations',
            manager_name='Manager',
            manager_email='manager@example.com',
            designation='Executive',
            monthly_compensation='25000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2026-03-01',
            contract_end_date=date(2026, 4, 1),
            is_active=False,
        )

        sent_count = send_daily_attendance_reminders(reference_date=date(2026, 4, 2))

        self.assertEqual(sent_count, 2)
        mocked_send.assert_any_call(self.employee_missing)
        mocked_send.assert_any_call(recently_inactive)

# Create your tests here.
