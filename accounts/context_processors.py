from .services import get_role_names, get_user_employee


def role_context(request):
    user = request.user
    if not user.is_authenticated:
        return {}

    roles = set(get_role_names(user))
    return {
        'current_roles': roles,
        'is_system_admin': 'system_admin' in roles,
        'is_hr_manager': 'system_admin' in roles or 'hr_manager' in roles,
        'is_finance_manager': 'system_admin' in roles or 'finance_manager' in roles,
        'current_employee': get_user_employee(user),
    }
