from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Employee(models.Model):
    class EmploymentType(models.TextChoices):
        EMPLOYEE = 'employee', 'Employee'
        INTERN = 'intern', 'Intern'
        CONSULTANT = 'consultant', 'Consultant'
        FREELANCER = 'freelancer', 'Freelancer'

    full_name = models.CharField(max_length=255)
    work_email = models.EmailField(unique=True)
    employment_type = models.CharField(max_length=32, choices=EmploymentType.choices)
    department = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    manager = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reportees',
    )
    monthly_compensation = models.DecimalField(max_digits=12, decimal_places=2)
    annual_leave_allowance = models.PositiveIntegerField(default=12)
    monthly_leave_cap = models.PositiveIntegerField(default=1)
    join_date = models.DateField()
    contract_end_date = models.DateField(null=True, blank=True)
    included_in_attendance = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('full_name',)

    def __str__(self):
        return self.full_name

    def clean(self):
        self.work_email = self.work_email.lower().strip()
        if self.contract_end_date and self.contract_end_date < self.join_date:
            raise ValidationError('Contract end date cannot be earlier than the joining date.')

    @property
    def current_contract(self):
        return self.contracts.filter(is_current=True).order_by('-uploaded_at').first()


class EmployeeContract(models.Model):
    employee = models.ForeignKey(Employee, related_name='contracts', on_delete=models.CASCADE)
    contract_file = models.FileField(upload_to='contracts/%Y/%m/')
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_contracts',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-uploaded_at',)

    def __str__(self):
        return f'{self.employee.full_name} contract ending {self.end_date}'

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError('Contract end date cannot be earlier than the start date.')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            self.employee.contracts.exclude(pk=self.pk).update(is_current=False)
            if self.employee.contract_end_date != self.end_date:
                self.employee.contract_end_date = self.end_date
                self.employee.save(update_fields=['contract_end_date', 'updated_at'])


class Holiday(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField(unique=True)
    is_ad_hoc = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('date',)

    def __str__(self):
        return f'{self.name} ({self.date})'


class ApprovedLeave(models.Model):
    employee = models.ForeignKey(Employee, related_name='approved_leaves', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_leaves',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-start_date', 'employee__full_name')

    def __str__(self):
        return f'{self.employee.full_name}: {self.start_date} to {self.end_date}'

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError('Leave end date cannot be earlier than the start date.')
