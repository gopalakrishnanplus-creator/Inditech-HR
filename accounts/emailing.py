import os

import requests
from django.core.exceptions import ValidationError

from .models import RoleAssignment
from .services import normalize_email


def get_active_hr_sender_email():
    explicit_sender = normalize_email(os.environ.get('HR_MANAGER_FROM_EMAIL'))
    if explicit_sender:
        return explicit_sender

    hr_assignment = RoleAssignment.objects.filter(
        role=RoleAssignment.Role.HR_MANAGER,
        active=True,
    ).order_by('created_at').first()
    if hr_assignment:
        return normalize_email(hr_assignment.email)
    return ''


def send_sendgrid_email(recipient_email, subject, body, sender_email=None):
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY', '').strip()
    sender_email = normalize_email(sender_email) or get_active_hr_sender_email()
    if not sendgrid_api_key:
        raise ValidationError('SENDGRID_API_KEY is not configured.')
    if not sender_email:
        raise ValidationError('No active HR manager email is configured for SendGrid emails.')

    payload = {
        'personalizations': [{'to': [{'email': normalize_email(recipient_email)}]}],
        'from': {'email': sender_email},
        'subject': subject,
        'content': [{'type': 'text/plain', 'value': body}],
    }
    response = requests.post(
        'https://api.sendgrid.com/v3/mail/send',
        json=payload,
        headers={
            'Authorization': f'Bearer {sendgrid_api_key}',
            'Content-Type': 'application/json',
        },
        timeout=30,
    )
    if response.status_code >= 300:
        raise ValidationError(
            f'SendGrid email failed for {recipient_email}: {response.status_code} {response.text}'
        )
