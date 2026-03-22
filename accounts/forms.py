from django import forms
from django.contrib.auth import authenticate

from .models import RoleAssignment
from .services import ensure_local_password_user, normalize_email


class RoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = RoleAssignment
        fields = ['display_name', 'email', 'role', 'active']


class LocalPasswordLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    error_messages = {
        'invalid_login': 'Invalid email or password.',
    }

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        email = normalize_email(cleaned_data.get('email'))
        password = cleaned_data.get('password')
        if not email or not password:
            return cleaned_data

        ensure_local_password_user(email)
        user = authenticate(self.request, username=email, password=password)
        if user is None:
            raise forms.ValidationError(self.error_messages['invalid_login'])

        self.user = user
        cleaned_data['email'] = email
        return cleaned_data

    def get_user(self):
        return self.user
