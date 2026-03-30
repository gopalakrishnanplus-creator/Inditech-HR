from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Employee, EmployeeContract


class EmployeeContractViewTests(TestCase):
    def setUp(self):
        self.user, _ = get_user_model().objects.get_or_create(
            username='gkinchina@gmail.com',
            defaults={
                'email': 'gkinchina@gmail.com',
                'is_active': True,
            },
        )
        self.user.email = 'gkinchina@gmail.com'
        self.user.set_password('password123')
        self.user.save()
        self.employee = Employee.objects.create(
            full_name='Contract Person',
            work_email='contract.person@example.com',
            employment_type=Employee.EmploymentType.EMPLOYEE,
            department='Human Resources',
            designation='Executive',
            monthly_compensation='35000.00',
            annual_leave_allowance=12,
            monthly_leave_cap=1,
            join_date='2026-01-01',
        )
        self.client.force_login(self.user)

    def test_contract_upload_redirects_with_see_other(self):
        response = self.client.post(
            reverse('hr:contract-create'),
            {
                'employee': self.employee.pk,
                'contract_file': SimpleUploadedFile('contract.txt', b'contract body'),
                'start_date': '2026-01-01',
                'end_date': '2026-12-31',
                'is_current': 'on',
                'notes': 'Initial contract',
            },
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['Location'], reverse('hr:contract-list'))
        self.assertEqual(EmployeeContract.objects.count(), 1)
