from django import forms

from .models import ApprovedLeave, Employee, EmployeeContract, Holiday


class DateInput(forms.DateInput):
    input_type = 'date'


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'full_name',
            'work_email',
            'employment_type',
            'department',
            'designation',
            'manager',
            'monthly_compensation',
            'annual_leave_allowance',
            'monthly_leave_cap',
            'join_date',
            'contract_end_date',
            'included_in_attendance',
            'is_active',
            'notes',
        ]
        widgets = {
            'join_date': DateInput(),
            'contract_end_date': DateInput(),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class EmployeeContractForm(forms.ModelForm):
    class Meta:
        model = EmployeeContract
        fields = ['employee', 'contract_file', 'start_date', 'end_date', 'is_current', 'notes']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = ['name', 'date', 'is_ad_hoc', 'notes']
        widgets = {
            'date': DateInput(),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class ApprovedLeaveForm(forms.ModelForm):
    class Meta:
        model = ApprovedLeave
        fields = ['employee', 'start_date', 'end_date', 'notes']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
