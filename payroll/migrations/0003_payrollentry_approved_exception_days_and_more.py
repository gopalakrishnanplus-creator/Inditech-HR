from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0002_managerpayrollapproval'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollentry',
            name='approved_comp_off_days',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='payrollentry',
            name='approved_exception_days',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
