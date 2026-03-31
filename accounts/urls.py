from django.urls import path

from .views import (
    AttendanceEntryView,
    AttendanceLoginView,
    AttendanceMissingDatesView,
    AttendanceSummaryView,
    DashboardView,
    LandingView,
    UpcomingContractListView,
    RoleAssignmentCreateView,
    RoleAssignmentListView,
    RoleAssignmentUpdateView,
)

app_name = 'accounts'

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('attendance-login/', AttendanceLoginView.as_view(), name='attendance-login'),
    path('attendance-entry/', AttendanceEntryView.as_view(), name='attendance-entry'),
    path('dashboard/contracts-ending/', UpcomingContractListView.as_view(), name='upcoming-contracts'),
    path('dashboard/attendance-summary/', AttendanceSummaryView.as_view(), name='attendance-summary'),
    path(
        'dashboard/attendance-summary/<int:pk>/absent-days/',
        AttendanceMissingDatesView.as_view(),
        name='attendance-missing-dates',
    ),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('roles/', RoleAssignmentListView.as_view(), name='role-list'),
    path('roles/new/', RoleAssignmentCreateView.as_view(), name='role-create'),
    path('roles/<int:pk>/edit/', RoleAssignmentUpdateView.as_view(), name='role-update'),
]
