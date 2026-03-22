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
    if email == normalize_email(settings.SYSTEM_ADMIN_EMAIL):
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


def ensure_default_system_admin():
    User = get_user_model()
    email = normalize_email(settings.SYSTEM_ADMIN_EMAIL)
    if not email:
        return None
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={'username': email, 'is_active': True},
    )
    if settings.LOCAL_PASSWORD_LOGIN_ENABLED:
        user.set_password(settings.LOCAL_DEV_DEFAULT_PASSWORD)
        user.save(update_fields=['password'])
    sync_user_permissions(user)
    return user


def ensure_local_password_user(email):
    email = normalize_email(email)
    if not settings.LOCAL_PASSWORD_LOGIN_ENABLED or not email:
        return None

    User = get_user_model()
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        allowed = (
            email == normalize_email(settings.SYSTEM_ADMIN_EMAIL)
            or Employee.objects.filter(work_email__iexact=email).exists()
            or RoleAssignment.objects.filter(email__iexact=email, active=True).exists()
        )
        if not allowed:
            return None
        user = User.objects.create_user(
            username=email,
            email=email,
            password=settings.LOCAL_DEV_DEFAULT_PASSWORD,
            is_active=True,
        )

    user.email = email
    if user.username != email:
        user.username = email
    user.set_password(settings.LOCAL_DEV_DEFAULT_PASSWORD)
    user.save(update_fields=['email', 'username', 'password'])
    sync_user_permissions(user)
    return user
