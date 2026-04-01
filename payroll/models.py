from django.conf import settings
from django.db import models

from hr.models import Employee


class PayrollRun(models.Model):
    payroll_month = models.DateField(unique=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payroll_runs',
    )
    generated_at = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-payroll_month',)

    def __str__(self):
        return self.payroll_month.strftime('%B %Y')


class ManagerPayrollApproval(models.Model):
    payroll_month = models.DateField()
    manager_name = models.CharField(max_length=255)
    manager_email = models.EmailField()
    comment = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='manager_payroll_approvals',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-payroll_month', 'manager_name', 'manager_email')
        unique_together = ('payroll_month', 'manager_email')

    def __str__(self):
        return f'{self.manager_name or self.manager_email} - {self.payroll_month.strftime("%B %Y")}'


class PayrollEntry(models.Model):
    run = models.ForeignKey(PayrollRun, related_name='entries', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, related_name='payroll_entries', on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    work_email = models.EmailField()
    employment_type = models.CharField(max_length=32)
    department = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    date_of_joining = models.DateField()
    contract_end_date = models.DateField(null=True, blank=True)
    annual_leave_allowance = models.PositiveIntegerField(default=0)
    annual_leave_used_before_month = models.PositiveIntegerField(default=0)
    monthly_leave_cap = models.PositiveIntegerField(default=0)
    total_calendar_days = models.PositiveIntegerField(default=0)
    active_calendar_days = models.PositiveIntegerField(default=0)
    working_days = models.PositiveIntegerField(default=0)
    holidays_in_month = models.PositiveIntegerField(default=0)
    present_days = models.PositiveIntegerField(default=0)
    approved_leave_days = models.PositiveIntegerField(default=0)
    approved_paid_leave_days = models.PositiveIntegerField(default=0)
    approved_lwp_days = models.PositiveIntegerField(default=0)
    unapproved_lwp_days = models.PositiveIntegerField(default=0)
    total_lwp_days = models.PositiveIntegerField(default=0)
    monthly_compensation = models.DecimalField(max_digits=12, decimal_places=2)
    per_day_deduction = models.DecimalField(max_digits=12, decimal_places=2)
    gross_payable = models.DecimalField(max_digits=12, decimal_places=2)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2)
    payment_decision = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('full_name',)
        unique_together = ('run', 'employee')

    def __str__(self):
        return f'{self.full_name} - {self.run}'

# Create your models here.
