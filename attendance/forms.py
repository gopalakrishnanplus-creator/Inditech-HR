from django import forms

from .models import AttendanceRecord


class AttendanceSubmissionForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['work_summary', 'supporting_file']
        widgets = {
            'work_summary': forms.Textarea(attrs={'rows': 6}),
        }
