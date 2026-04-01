from django.contrib import admin

from .models import ManagerPayrollApproval, PayrollEntry, PayrollRun


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('payroll_month', 'generated_by', 'generated_at')


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'run', 'monthly_compensation', 'total_lwp_days', 'net_payable')
    list_filter = ('employment_type', 'department')
    search_fields = ('full_name', 'work_email')


@admin.register(ManagerPayrollApproval)
class ManagerPayrollApprovalAdmin(admin.ModelAdmin):
    list_display = ('payroll_month', 'manager_name', 'manager_email', 'approved_at', 'notification_sent_at')
    list_filter = ('payroll_month',)
    search_fields = ('manager_name', 'manager_email')

# Register your models here.
