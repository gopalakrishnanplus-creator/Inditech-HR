from django.urls import path

from .views import DashboardView, LandingView, LocalLoginView, RoleAssignmentCreateView, RoleAssignmentListView, RoleAssignmentUpdateView

app_name = 'accounts'

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('login/', LocalLoginView.as_view(), name='login'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('roles/', RoleAssignmentListView.as_view(), name='role-list'),
    path('roles/new/', RoleAssignmentCreateView.as_view(), name='role-create'),
    path('roles/<int:pk>/edit/', RoleAssignmentUpdateView.as_view(), name='role-update'),
]
