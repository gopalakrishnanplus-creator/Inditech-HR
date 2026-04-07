import json
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from accounts.emailing import get_sendgrid_debug_snapshot, send_sendgrid_email


class Command(BaseCommand):
    help = 'Send a single SendGrid test email with detailed debug output.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recipient',
            default='gopala.krishnan@inditech.co.in',
            help='Recipient email address. Defaults to gopala.krishnan@inditech.co.in',
        )
        parser.add_argument(
            '--sender',
            default='',
            help='Optional sender email override. Defaults to resolved HR manager sender.',
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        sender = options['sender'] or None
        timestamp = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        subject = f'Inditech HR SendGrid test email {timestamp}'
        body = (
            'This is a test email from the Inditech HR SendGrid debug command.\n\n'
            'If you received this, the EC2 server was able to resolve the sender and talk to SendGrid successfully.'
        )

        debug_snapshot = get_sendgrid_debug_snapshot(recipient, sender_email=sender)
        self.stdout.write('Pre-send debug snapshot:')
        self.stdout.write(json.dumps(debug_snapshot, indent=2, sort_keys=True))

        try:
            result = send_sendgrid_email(
                recipient,
                subject,
                body,
                sender_email=sender,
                debug=True,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write('SendGrid send result:')
        self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
        self.stdout.write(self.style.SUCCESS(f'Test email sent successfully to {recipient}.'))
