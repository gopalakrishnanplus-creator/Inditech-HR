from django.db import migrations, models


def copy_manager_details(apps, schema_editor):
    Employee = apps.get_model('hr', 'Employee')
    for employee in Employee.objects.select_related('manager').exclude(manager=None):
        employee.manager_name = employee.manager.full_name
        employee.manager_email = employee.manager.work_email
        employee.save(update_fields=['manager_name', 'manager_email'])


class Migration(migrations.Migration):
    dependencies = [
        ('hr', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='manager_email',
            field=models.EmailField(blank=True, default='', max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='employee',
            name='manager_name',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
        migrations.RunPython(copy_manager_details, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='employee',
            name='manager',
        ),
    ]
