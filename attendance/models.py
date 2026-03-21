from django.db import models
from django.utils import timezone

from hr.models import Employee


class AttendanceRecord(models.Model):
    employee = models.ForeignKey(Employee, related_name='attendance_records', on_delete=models.CASCADE)
    attendance_date = models.DateField(editable=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    employee_name = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=32, choices=Employee.EmploymentType.choices)
    reports_to_name = models.CharField(max_length=255, blank=True)
    work_summary = models.TextField()
    supporting_file = models.FileField(upload_to='attendance/%Y/%m/', blank=True, null=True)

    class Meta:
        ordering = ('-attendance_date', '-submitted_at')
        constraints = [
            models.UniqueConstraint(fields=('employee', 'attendance_date'), name='unique_employee_daily_attendance')
        ]

    def __str__(self):
        return f'{self.employee_name} - {self.attendance_date}'

    def save(self, *args, **kwargs):
        self.employee_name = self.employee.full_name
        self.employment_type = self.employee.employment_type
        self.reports_to_name = self.employee.manager.full_name if self.employee.manager else ''
        if not self.attendance_date:
            self.attendance_date = timezone.localdate()
        super().save(*args, **kwargs)

# Create your models here.
