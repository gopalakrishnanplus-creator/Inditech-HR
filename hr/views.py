from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import HttpResponseRedirectBase
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from accounts.permissions import FinanceManagerRequiredMixin, HRManagerRequiredMixin

from .forms import ApprovedLeaveForm, EmployeeContractForm, EmployeeForm, HolidayForm
from .models import ApprovedLeave, Employee, EmployeeContract, Holiday


class HttpResponseSeeOther(HttpResponseRedirectBase):
    status_code = 303


class EmployeeListView(HRManagerRequiredMixin, ListView):
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'


class EmployeeCreateView(HRManagerRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee-list')

    def form_valid(self, form):
        messages.success(self.request, 'Employee saved.')
        return super().form_valid(form)


class EmployeeUpdateView(HRManagerRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee-list')

    def form_valid(self, form):
        messages.success(self.request, 'Employee updated.')
        return super().form_valid(form)


class EmployeeContractListView(HRManagerRequiredMixin, ListView):
    model = EmployeeContract
    template_name = 'hr/contract_list.html'
    context_object_name = 'contracts'


class EmployeeContractCreateView(HRManagerRequiredMixin, CreateView):
    model = EmployeeContract
    form_class = EmployeeContractForm
    template_name = 'hr/contract_form.html'
    success_url = reverse_lazy('hr:contract-list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        self.object = form.save()
        messages.success(self.request, 'Contract uploaded.')
        return HttpResponseSeeOther(self.get_success_url())


class EmployeeContractUpdateView(HRManagerRequiredMixin, UpdateView):
    model = EmployeeContract
    form_class = EmployeeContractForm
    template_name = 'hr/contract_form.html'
    success_url = reverse_lazy('hr:contract-list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'Contract updated.')
        return HttpResponseSeeOther(self.get_success_url())


class HolidayListView(LoginRequiredMixin, ListView):
    model = Holiday
    template_name = 'hr/holiday_list.html'
    context_object_name = 'holidays'


class HolidayCreateView(FinanceManagerRequiredMixin, CreateView):
    model = Holiday
    form_class = HolidayForm
    template_name = 'hr/holiday_form.html'
    success_url = reverse_lazy('hr:holiday-list')

    def form_valid(self, form):
        messages.success(self.request, 'Holiday saved.')
        return super().form_valid(form)


class HolidayUpdateView(FinanceManagerRequiredMixin, UpdateView):
    model = Holiday
    form_class = HolidayForm
    template_name = 'hr/holiday_form.html'
    success_url = reverse_lazy('hr:holiday-list')

    def form_valid(self, form):
        messages.success(self.request, 'Holiday updated.')
        return super().form_valid(form)


class ApprovedLeaveListView(FinanceManagerRequiredMixin, ListView):
    model = ApprovedLeave
    template_name = 'hr/leave_list.html'
    context_object_name = 'leaves'


class ApprovedLeaveCreateView(FinanceManagerRequiredMixin, CreateView):
    model = ApprovedLeave
    form_class = ApprovedLeaveForm
    template_name = 'hr/leave_form.html'
    success_url = reverse_lazy('hr:leave-list')

    def form_valid(self, form):
        form.instance.approved_by = self.request.user
        messages.success(self.request, 'Approved leave saved.')
        return super().form_valid(form)


class ApprovedLeaveUpdateView(FinanceManagerRequiredMixin, UpdateView):
    model = ApprovedLeave
    form_class = ApprovedLeaveForm
    template_name = 'hr/leave_form.html'
    success_url = reverse_lazy('hr:leave-list')

    def form_valid(self, form):
        form.instance.approved_by = self.request.user
        messages.success(self.request, 'Approved leave updated.')
        return super().form_valid(form)

# Create your views here.
