from django import forms

from .models import ManagerPayrollApproval, PayrollEntry


class MonthInput(forms.DateInput):
    input_type = 'month'


class PayrollGenerationForm(forms.Form):
    payroll_month = forms.DateField(widget=MonthInput(), input_formats=['%Y-%m'])

    def clean_payroll_month(self):
        month_value = self.cleaned_data['payroll_month']
        return month_value.replace(day=1)


class PayrollEntryDecisionForm(forms.ModelForm):
    class Meta:
        model = PayrollEntry
        fields = ['payment_decision']
        widgets = {
            'payment_decision': forms.Textarea(attrs={'rows': 4}),
        }


class ManagerPayrollApprovalForm(forms.ModelForm):
    class Meta:
        model = ManagerPayrollApproval
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4}),
        }
