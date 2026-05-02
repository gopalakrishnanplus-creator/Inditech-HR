from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from attendance.models import AttendanceRecord
from hr.models import Employee, Holiday
from hr.services import get_working_dates, month_bounds

from .forms import RoleAssignmentForm
from .models import RoleAssignment
from .permissions import HRManagerRequiredMixin, SystemAdminRequiredMixin
from .services import get_role_names, get_user_employee, sync_user_permissions


def get_upcoming_contract_queryset(reference_date):
    return Employee.objects.filter(
        join_date__lte=reference_date,
        contract_end_date__range=(reference_date, reference_date + timedelta(days=30)),
    ).order_by('contract_end_date', 'full_name')


def get_attendance_period(month_key, reference_date):
    if month_key == 'previous':
        previous_month_reference = reference_date.replace(day=1) - timedelta(days=1)
        month_start, month_end = month_bounds(previous_month_reference)
        month_label = previous_month_reference.strftime('%B %Y')
    else:
        month_start = reference_date.replace(day=1)
        month_end = reference_date
        month_label = reference_date.strftime('%B %Y')
    return month_start, month_end, month_label


def get_employee_missing_attendance_dates(employee, month_key, reference_date, holiday_dates=None):
    month_start, month_end, _ = get_attendance_period(month_key, reference_date)
    holiday_dates = holiday_dates or set(
        Holiday.objects.filter(date__range=(month_start, month_end)).values_list('date', flat=True)
    )
    period_start = max(month_start, employee.join_date)
    period_end = min(month_end, employee.contract_end_date) if employee.contract_end_date else month_end
    if period_end < period_start:
        return []

    expected_dates = get_working_dates(period_start, period_end, holiday_dates)
    submitted_dates = set(
        AttendanceRecord.objects.filter(
            employee=employee,
            attendance_date__range=(period_start, period_end),
        ).values_list('attendance_date', flat=True)
    )
    return [current_date for current_date in expected_dates if current_date not in submitted_dates]


def get_attendance_summary_rows(month_key, reference_date):
    month_start, month_end, _ = get_attendance_period(month_key, reference_date)
    employees = list(
        Employee.objects.filter(
            included_in_attendance=True,
            join_date__lte=month_end,
        ).exclude(contract_end_date__lt=month_start).order_by('full_name')
    )
    holiday_dates = set(Holiday.objects.filter(date__range=(month_start, month_end)).values_list('date', flat=True))
    attendance_by_employee = defaultdict(set)
    for employee_id, attendance_date in AttendanceRecord.objects.filter(
        employee__in=employees,
        attendance_date__range=(month_start, month_end),
    ).values_list('employee_id', 'attendance_date'):
        attendance_by_employee[employee_id].add(attendance_date)

    rows = []
    for employee in employees:
        missing_dates = get_employee_missing_attendance_dates(
            employee,
            month_key,
            reference_date,
            holiday_dates=holiday_dates,
        )
        submitted_dates = attendance_by_employee.get(employee.pk, set())
        rows.append(
            {
                'employee': employee,
                'submitted_days': len(submitted_dates),
                'missing_days_count': len(missing_dates),
            }
        )
    return rows


class LandingView(TemplateView):
    template_name = 'accounts/landing.html'


class AttendanceLoginView(TemplateView):
    template_name = 'accounts/attendance_login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:attendance-entry')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendance_entry_url'] = reverse_lazy('accounts:attendance-entry')
        return context


class AttendanceEntryView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        sync_user_permissions(request.user)
        if get_user_employee(request.user):
            return redirect('attendance:submit')
        messages.error(request, 'This sign-in link is only for employees, interns, and consultants with attendance access.')
        return redirect('accounts:dashboard')


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
                'pending_contracts': get_upcoming_contract_queryset(today).count(),
            }
        )
        return context


class UpcomingContractListView(HRManagerRequiredMixin, ListView):
    model = Employee
    template_name = 'accounts/upcoming_contracts.html'
    context_object_name = 'employees'

    def get_queryset(self):
        self.today = timezone.localdate()
        return get_upcoming_contract_queryset(self.today)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = self.today
        context['window_end'] = self.today + timedelta(days=30)
        return context


class AttendanceSummaryView(HRManagerRequiredMixin, TemplateView):
    template_name = 'accounts/attendance_summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_key = 'previous' if self.request.GET.get('month') == 'previous' else 'current'
        month_start, month_end, month_label = get_attendance_period(month_key, today)
        context.update(
            {
                'today': today,
                'month_key': month_key,
                'month_start': month_start,
                'month_end': month_end,
                'month_label': month_label,
                'rows': get_attendance_summary_rows(month_key, today),
            }
        )
        return context


class AttendanceMissingDatesView(HRManagerRequiredMixin, TemplateView):
    template_name = 'accounts/attendance_missing_dates.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_key = 'previous' if self.request.GET.get('month') == 'previous' else 'current'
        month_start, month_end, month_label = get_attendance_period(month_key, today)
        employee = Employee.objects.get(pk=self.kwargs['pk'])
        context.update(
            {
                'today': today,
                'month_key': month_key,
                'month_start': month_start,
                'month_end': month_end,
                'month_label': month_label,
                'employee': employee,
                'missing_dates': get_employee_missing_attendance_dates(employee, month_key, today),
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
