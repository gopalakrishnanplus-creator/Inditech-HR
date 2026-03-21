from django.contrib import admin

from .models import PayrollEntry, PayrollRun


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('payroll_month', 'generated_by', 'generated_at')


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'run', 'monthly_compensation', 'total_lwp_days', 'net_payable')
    list_filter = ('employment_type', 'department')
    search_fields = ('full_name', 'work_email')

# Register your models here.
