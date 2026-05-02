from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('hr', '0002_employee_manager_contact_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='approvedleave',
            name='leave_type',
            field=models.CharField(
                choices=[
                    ('regular_leave', 'Leave'),
                    ('exception_approval', 'Exception approval'),
                    ('comp_off', 'Comp-off'),
                ],
                default='regular_leave',
                max_length=32,
            ),
        ),
    ]
