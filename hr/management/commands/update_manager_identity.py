from django.core.management.base import BaseCommand

from accounts.services import normalize_email
from hr.models import Employee


class Command(BaseCommand):
    help = 'Update employee manager name/email values matching a known incorrect manager identity.'

    def add_arguments(self, parser):
        parser.add_argument('--from-name', required=True)
        parser.add_argument('--from-email', required=True)
        parser.add_argument('--to-name', required=True)
        parser.add_argument('--to-email', required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        from_name = options['from_name'].strip()
        from_email = normalize_email(options['from_email'])
        to_name = options['to_name'].strip()
        to_email = normalize_email(options['to_email'])

        employees = list(
            Employee.objects.filter(manager_email__iexact=from_email, manager_name__iexact=from_name)
            .order_by('full_name')
        )
        self.stdout.write(f'Found {len(employees)} employee(s) matching manager {from_name} <{from_email}>.')
        for employee in employees:
            self.stdout.write(
                f'- {employee.full_name} ({employee.work_email}): '
                f'{employee.manager_name} <{employee.manager_email}> -> {to_name} <{to_email}>'
            )

        if not options['apply']:
            self.stdout.write('Dry run only. Re-run with --apply to update these records.')
            return

        updated = 0
        for employee in employees:
            employee.manager_name = to_name
            employee.manager_email = to_email
            employee.save(update_fields=['manager_name', 'manager_email', 'updated_at'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Updated {updated} employee manager assignment(s).'))
