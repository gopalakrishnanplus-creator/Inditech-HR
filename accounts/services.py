from django.conf import settings
from django.contrib.auth import get_user_model

from hr.models import Employee

from .models import RoleAssignment


def normalize_email(email):
    return (email or '').strip().lower()


def get_role_names(user):
    if not user or not user.is_authenticated:
        return []

    email = normalize_email(user.email)
    roles = []
    if email in set(settings.SYSTEM_ADMIN_EMAILS):
        roles.append('system_admin')

    roles.extend(
        RoleAssignment.objects.filter(email__iexact=email, active=True).values_list('role', flat=True)
    )
    return list(dict.fromkeys(roles))


def get_user_employee(user):
    if not user or not user.is_authenticated:
        return None
    email = normalize_email(user.email)
    if not email:
        return None
    return Employee.objects.filter(work_email__iexact=email).first()


def sync_user_permissions(user):
    if not user:
        return

    roles = set(get_role_names(user))
    user.is_staff = bool(roles.intersection({'system_admin', 'hr_manager', 'finance_manager'}))
    user.is_superuser = 'system_admin' in roles
    if user.email:
        user.email = normalize_email(user.email)
        if not user.username:
            user.username = user.email
    user.save(update_fields=['email', 'username', 'is_staff', 'is_superuser'])


def is_allowed_email(email):
    email = normalize_email(email)
    if not email:
        return False
    return (
        email in set(settings.SYSTEM_ADMIN_EMAILS)
        or Employee.objects.filter(work_email__iexact=email).exists()
        or RoleAssignment.objects.filter(email__iexact=email, active=True).exists()
    )


def ensure_default_system_admins():
    User = get_user_model()
    created_users = []
    for email in settings.SYSTEM_ADMIN_EMAILS:
        user, _ = User.objects.get_or_create(
            username=email,
            email=email,
            defaults={'is_active': True},
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        sync_user_permissions(user)
        created_users.append(user)
    return created_users
