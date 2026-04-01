from datetime import date

from django.core.management.base import BaseCommand, CommandError

from payroll.services import send_manager_payroll_approval_requests


class Command(BaseCommand):
    help = 'Send previous-month payroll approval emails to managers.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Send even if today is not the first of the month.')
        parser.add_argument(
            '--date',
            help='Override the reference date in YYYY-MM-DD format.',
        )

    def handle(self, *args, **options):
        reference_date = None
        if options['date']:
            try:
                reference_date = date.fromisoformat(options['date'])
            except ValueError as exc:
                raise CommandError('Invalid --date. Use YYYY-MM-DD.') from exc

        sent_count = send_manager_payroll_approval_requests(
            reference_date=reference_date,
            force=options['force'],
        )
        self.stdout.write(self.style.SUCCESS(f'Sent {sent_count} manager payroll approval email(s).'))
