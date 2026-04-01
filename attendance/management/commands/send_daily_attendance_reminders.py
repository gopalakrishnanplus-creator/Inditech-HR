from datetime import date

from django.core.management.base import BaseCommand, CommandError

from attendance.services import send_daily_attendance_reminders


class Command(BaseCommand):
    help = 'Send attendance reminder emails for the previous working day.'

    def add_arguments(self, parser):
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

        sent_count = send_daily_attendance_reminders(reference_date=reference_date)
        self.stdout.write(self.style.SUCCESS(f'Sent {sent_count} attendance reminder email(s).'))
