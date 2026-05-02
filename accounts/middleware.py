from django.shortcuts import redirect
from django.urls import reverse

from .services import get_role_names, get_user_employee


class ManagerPortalRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_exact_paths = {
            reverse('payroll:manager-approval'),
            reverse('account_logout'),
        }
        self.employee_allowed_exact_paths = {
            reverse('accounts:attendance-login'),
            reverse('accounts:attendance-entry'),
            reverse('hr:holiday-list'),
        }
        self.employee_allowed_prefixes = (
            '/attendance/',
        )
        self.allowed_prefixes = (
            '/accounts/',
        )

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            roles = set(get_role_names(user))
            if roles == {'manager_payroll_approver'}:
                path = request.path
                is_allowed_path = path in self.allowed_exact_paths or any(
                    path.startswith(prefix) for prefix in self.allowed_prefixes
                )
                is_employee_attendance_path = get_user_employee(user) and (
                    path in self.employee_allowed_exact_paths
                    or any(path.startswith(prefix) for prefix in self.employee_allowed_prefixes)
                )
                if not is_allowed_path and not is_employee_attendance_path:
                    return redirect('payroll:manager-approval')
        return self.get_response(request)
