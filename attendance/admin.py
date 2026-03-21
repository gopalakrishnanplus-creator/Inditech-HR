from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('employee_name', 'attendance_date', 'employment_type', 'reports_to_name', 'submitted_at')
    list_filter = ('employment_type', 'attendance_date')
    search_fields = ('employee_name', 'reports_to_name', 'work_summary')

# Register your models here.
