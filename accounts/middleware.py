from django.shortcuts import redirect
from django.urls import reverse

from .services import get_role_names


class ManagerPortalRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_exact_paths = {
            reverse('payroll:manager-approval'),
            reverse('account_logout'),
        }
        self.allowed_prefixes = (
            '/accounts/',
        )

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            roles = set(get_role_names(user))
            if roles == {'manager_payroll_approver'}:
                path = request.path
                if path not in self.allowed_exact_paths and not any(
                    path.startswith(prefix) for prefix in self.allowed_prefixes
                ):
                    return redirect('payroll:manager-approval')
        return self.get_response(request)
