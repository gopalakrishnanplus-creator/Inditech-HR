from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from attendance.models import AttendanceRecord
from hr.models import Employee

from .forms import RoleAssignmentForm
from .models import RoleAssignment
from .permissions import SystemAdminRequiredMixin
from .services import get_role_names, get_user_employee, sync_user_permissions


class LandingView(TemplateView):
    template_name = 'accounts/landing.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        sync_user_permissions(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = get_user_employee(self.request.user)
        today = timezone.localdate()
        context.update(
            {
                'employee': employee,
                'today': today,
                'role_names': get_role_names(self.request.user),
                'today_attendance': (
                    AttendanceRecord.objects.filter(employee=employee, attendance_date=today).first()
                    if employee
                    else None
                ),
                'employee_count': Employee.objects.count(),
                'pending_contracts': Employee.objects.filter(contract_end_date__lt=today + timedelta(days=30)).count(),
            }
        )
        return context


class RoleAssignmentListView(SystemAdminRequiredMixin, ListView):
    model = RoleAssignment
    template_name = 'accounts/roleassignment_list.html'
    context_object_name = 'assignments'


class RoleAssignmentCreateView(SystemAdminRequiredMixin, CreateView):
    model = RoleAssignment
    form_class = RoleAssignmentForm
    template_name = 'accounts/roleassignment_form.html'
    success_url = reverse_lazy('accounts:role-list')

    def form_valid(self, form):
        messages.success(self.request, 'Role assignment created.')
        return super().form_valid(form)


class RoleAssignmentUpdateView(SystemAdminRequiredMixin, UpdateView):
    model = RoleAssignment
    form_class = RoleAssignmentForm
    template_name = 'accounts/roleassignment_form.html'
    success_url = reverse_lazy('accounts:role-list')

    def form_valid(self, form):
        messages.success(self.request, 'Role assignment updated.')
        return super().form_valid(form)

# Create your views here.
