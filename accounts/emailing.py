import os
from typing import Any

import requests
from django.core.exceptions import ValidationError

from .models import RoleAssignment
from .services import normalize_email


def mask_secret(value, keep=4):
    if not value:
        return ''
    if len(value) <= keep:
        return '*' * len(value)
    return ('*' * max(len(value) - keep, 0)) + value[-keep:]


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


def get_sendgrid_debug_snapshot(recipient_email, sender_email=None) -> dict[str, Any]:
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY', '').strip()
    configured_sender_email = normalize_email(sender_email)
    resolved_sender_email = configured_sender_email or get_active_hr_sender_email()
    hr_assignment = RoleAssignment.objects.filter(
        role=RoleAssignment.Role.HR_MANAGER,
        active=True,
    ).order_by('created_at').first()
    return {
        'recipient_email': normalize_email(recipient_email),
        'provided_sender_email': configured_sender_email,
        'resolved_sender_email': resolved_sender_email,
        'active_hr_manager_email': normalize_email(hr_assignment.email) if hr_assignment else '',
        'sendgrid_api_key_present': bool(sendgrid_api_key),
        'sendgrid_api_key_masked': mask_secret(sendgrid_api_key),
        'app_base_url': os.environ.get('APP_BASE_URL', ''),
        'hr_manager_from_email_env': normalize_email(os.environ.get('HR_MANAGER_FROM_EMAIL')),
    }


def send_sendgrid_email(recipient_email, subject, body, sender_email=None, debug=False):
    debug_snapshot = get_sendgrid_debug_snapshot(recipient_email, sender_email=sender_email)
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY', '').strip()
    sender_email = debug_snapshot['resolved_sender_email']
    if not sendgrid_api_key:
        raise ValidationError(f"SENDGRID_API_KEY is not configured. Debug: {debug_snapshot}")
    if not sender_email:
        raise ValidationError(f"No active HR manager email is configured for SendGrid emails. Debug: {debug_snapshot}")

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
    result = {
        **debug_snapshot,
        'subject': subject,
        'payload_to': payload['personalizations'][0]['to'][0]['email'],
        'status_code': response.status_code,
        'response_text_excerpt': response.text[:1000],
        'sendgrid_message_id': response.headers.get('X-Message-Id', ''),
    }
    if response.status_code >= 300:
        raise ValidationError(
            f"SendGrid email failed for {recipient_email}: {response.status_code} {response.text}. Debug: {result}"
        )
    if debug:
        return result
    return None
