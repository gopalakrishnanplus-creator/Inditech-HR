from django.contrib import admin

from .models import RoleAssignment


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'active')
    list_filter = ('role', 'active')
    search_fields = ('email', 'display_name')

# Register your models here.
