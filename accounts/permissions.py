from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from .services import get_role_names, get_user_employee


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    required_roles = ()

    def test_func(self):
        roles = set(get_role_names(self.request.user))
        if 'system_admin' in roles:
            return True
        return bool(roles.intersection(self.required_roles))

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class SystemAdminRequiredMixin(RoleRequiredMixin):
    required_roles = ('system_admin',)

    def test_func(self):
        return 'system_admin' in set(get_role_names(self.request.user))


class HRManagerRequiredMixin(RoleRequiredMixin):
    required_roles = ('hr_manager',)


class FinanceManagerRequiredMixin(RoleRequiredMixin):
    required_roles = ('finance_manager', 'hr_manager')


class ManagerPayrollRequiredMixin(RoleRequiredMixin):
    required_roles = ('manager_payroll_approver',)


class EmployeeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return get_user_employee(self.request.user) is not None

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()
