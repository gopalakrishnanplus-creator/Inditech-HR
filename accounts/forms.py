from django import forms

from .models import RoleAssignment


class RoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = RoleAssignment
        fields = ['display_name', 'email', 'role', 'active']
