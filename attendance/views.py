from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, ListView

from accounts.permissions import EmployeeRequiredMixin
from accounts.services import get_user_employee

from .forms import AttendanceSubmissionForm
from .models import AttendanceRecord
from .services import has_approved_leave_on_date


class AttendanceSubmitView(EmployeeRequiredMixin, FormView):
    form_class = AttendanceSubmissionForm
    template_name = 'attendance/submit.html'
    success_url = reverse_lazy('attendance:submit')

    def dispatch(self, request, *args, **kwargs):
        self.employee = get_user_employee(request.user)
        self.today = timezone.localdate()
        self.today_record = AttendanceRecord.objects.filter(employee=self.employee, attendance_date=self.today).first()
        self.approved_leave_today = has_approved_leave_on_date(self.employee, self.today)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'hide_management_nav': True,
                'employee': self.employee,
                'today': self.today,
                'today_record': self.today_record,
                'approved_leave_today': self.approved_leave_today,
            }
        )
        return context

    def form_valid(self, form):
        if self.approved_leave_today:
            messages.error(self.request, 'You cannot fill in attendance for today because you are on approved leave.')
            return redirect(self.success_url)
        if self.today_record:
            messages.error(self.request, 'Attendance has already been submitted for today.')
            return redirect(self.success_url)

        record = form.save(commit=False)
        record.employee = self.employee
        record.save()
        messages.success(self.request, 'Attendance submitted.')
        return super().form_valid(form)


class AttendanceHistoryView(EmployeeRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = 'attendance/history.html'
    context_object_name = 'records'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_management_nav'] = True
        return context

    def get_queryset(self):
        employee = get_user_employee(self.request.user)
        return AttendanceRecord.objects.filter(employee=employee)

# Create your views here.
