from django.core.exceptions import ValidationError
from django.db import models


class RoleAssignment(models.Model):
    class Role(models.TextChoices):
        HR_MANAGER = 'hr_manager', 'HR manager'
        FINANCE_MANAGER = 'finance_manager', 'Finance manager'

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=32, choices=Role.choices)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('role', 'email')

    def __str__(self):
        return f'{self.email} ({self.get_role_display()})'

    def clean(self):
        self.email = self.email.lower().strip()
        if self.active and self.role == self.Role.FINANCE_MANAGER:
            qs = RoleAssignment.objects.filter(role=self.Role.FINANCE_MANAGER, active=True).exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('Only one active finance manager email can be configured at a time.')

# Create your models here.
