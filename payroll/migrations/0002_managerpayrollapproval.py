import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagerPayrollApproval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payroll_month', models.DateField()),
                ('manager_name', models.CharField(max_length=255)),
                ('manager_email', models.EmailField(max_length=254)),
                ('comment', models.TextField(blank=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('notification_sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='manager_payroll_approvals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-payroll_month', 'manager_name', 'manager_email'),
                'unique_together': {('payroll_month', 'manager_email')},
            },
        ),
    ]
