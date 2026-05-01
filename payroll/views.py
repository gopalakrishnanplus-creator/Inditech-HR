from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView

from accounts.permissions import FinanceManagerRequiredMixin, HRManagerRequiredMixin, ManagerPayrollRequiredMixin
from accounts.services import normalize_email

from .forms import ManagerPayrollApprovalForm, PayrollEntryDecisionForm, PayrollGenerationForm
from .models import ManagerPayrollApproval, PayrollEntry, PayrollRun
from .services import (
    generate_payroll_run,
    get_manager_approval_groups,
    get_manager_group_for_email,
    get_previous_month_start,
)


class PayrollRunListView(FinanceManagerRequiredMixin, ListView):
    model = PayrollRun
    template_name = 'payroll/run_list.html'
    context_object_name = 'runs'


class PayrollGenerateView(FinanceManagerRequiredMixin, FormView):
    form_class = PayrollGenerationForm
    template_name = 'payroll/generate.html'
    success_url = reverse_lazy('payroll:run-list')

    def form_valid(self, form):
        try:
            run = generate_payroll_run(form.cleaned_data['payroll_month'], self.request.user)
        except ValidationError as exc:
            form.add_error('payroll_month', exc.message)
            return self.form_invalid(form)

        messages.success(self.request, f'Payroll generated for {run}.')
        self.success_url = reverse_lazy('payroll:run-detail', kwargs={'pk': run.pk})
        return super().form_valid(form)


class PayrollRunDetailView(FinanceManagerRequiredMixin, DetailView):
    model = PayrollRun
    template_name = 'payroll/run_detail.html'
    context_object_name = 'run'


class PayrollEntryUpdateView(FinanceManagerRequiredMixin, UpdateView):
    model = PayrollEntry
    form_class = PayrollEntryDecisionForm
    template_name = 'payroll/entry_form.html'

    def get_success_url(self):
        return reverse_lazy('payroll:run-detail', kwargs={'pk': self.object.run_id})

    def form_valid(self, form):
        messages.success(self.request, 'Payment decision updated.')
        return super().form_valid(form)


class PayrollApprovalReviewView(HRManagerRequiredMixin, TemplateView):
    template_name = 'payroll/approval_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payroll_month = get_previous_month_start(timezone.localdate())
        context.update(
            {
                'payroll_month': payroll_month,
                'groups': get_manager_approval_groups(payroll_month),
            }
        )
        return context


class ManagerPayrollApprovalDashboardView(ManagerPayrollRequiredMixin, LoginRequiredMixin, FormView):
    form_class = ManagerPayrollApprovalForm
    template_name = 'payroll/manager_approval.html'
    success_url = reverse_lazy('payroll:manager-approval')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.payroll_month = get_previous_month_start(timezone.localdate())
        self.manager_email = normalize_email(request.user.email)
        self.group = get_manager_group_for_email(self.manager_email, self.payroll_month)
        if not self.group:
            messages.error(request, 'No payroll review items are assigned to this manager email for the previous month.')
            return redirect('accounts:dashboard')
        self.approval, _ = ManagerPayrollApproval.objects.get_or_create(
            payroll_month=self.payroll_month,
            manager_email=self.manager_email,
            defaults={'manager_name': self.group['manager_name']},
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.approval
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'hide_management_nav': True,
                'payroll_month': self.payroll_month,
                'group': self.group,
                'approval': self.approval,
            }
        )
        return context

    def form_valid(self, form):
        approval = form.save(commit=False)
        approval.payroll_month = self.payroll_month
        approval.manager_email = self.manager_email
        approval.manager_name = self.group['manager_name']
        approval.approved_by = self.request.user
        approval.approved_at = timezone.now()
        approval.save()
        messages.success(self.request, 'Payroll review submitted successfully.')
        return super().form_valid(form)

# Create your views here.
