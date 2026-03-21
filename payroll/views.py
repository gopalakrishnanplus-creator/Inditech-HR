from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, DetailView, UpdateView

from accounts.permissions import FinanceManagerRequiredMixin

from .forms import PayrollEntryDecisionForm, PayrollGenerationForm
from .models import PayrollEntry, PayrollRun
from .services import generate_payroll_run


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

# Create your views here.
