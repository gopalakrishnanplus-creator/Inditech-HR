from django.contrib import admin

from .models import ApprovedLeave, Employee, EmployeeContract, Holiday


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'work_email',
        'employment_type',
        'department',
        'manager_name',
        'manager_email',
        'monthly_compensation',
        'contract_end_date',
        'is_active',
    )
    list_filter = ('employment_type', 'department', 'included_in_attendance', 'is_active')
    search_fields = ('full_name', 'work_email', 'designation', 'manager_name', 'manager_email')


@admin.register(EmployeeContract)
class EmployeeContractAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_date', 'end_date', 'is_current', 'uploaded_at')
    list_filter = ('is_current',)
    search_fields = ('employee__full_name',)


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'is_ad_hoc')
    list_filter = ('is_ad_hoc',)
    search_fields = ('name',)


@admin.register(ApprovedLeave)
class ApprovedLeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_date', 'end_date', 'approved_by')
    search_fields = ('employee__full_name',)

# Register your models here.
