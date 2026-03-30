from django.urls import path

from .views import (
    AttendanceEntryView,
    AttendanceLoginView,
    DashboardView,
    LandingView,
    RoleAssignmentCreateView,
    RoleAssignmentListView,
    RoleAssignmentUpdateView,
)

app_name = 'accounts'

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('attendance-login/', AttendanceLoginView.as_view(), name='attendance-login'),
    path('attendance-entry/', AttendanceEntryView.as_view(), name='attendance-entry'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('roles/', RoleAssignmentListView.as_view(), name='role-list'),
    path('roles/new/', RoleAssignmentCreateView.as_view(), name='role-create'),
    path('roles/<int:pk>/edit/', RoleAssignmentUpdateView.as_view(), name='role-update'),
]
