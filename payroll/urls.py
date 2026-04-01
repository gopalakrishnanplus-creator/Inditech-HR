from django.urls import path

from .views import (
    ManagerPayrollApprovalDashboardView,
    PayrollApprovalReviewView,
    PayrollEntryUpdateView,
    PayrollGenerateView,
    PayrollRunDetailView,
    PayrollRunListView,
)

app_name = 'payroll'

urlpatterns = [
    path('', PayrollRunListView.as_view(), name='run-list'),
    path('generate/', PayrollGenerateView.as_view(), name='generate'),
    path('review/', PayrollApprovalReviewView.as_view(), name='approval-review'),
    path('manager-approval/', ManagerPayrollApprovalDashboardView.as_view(), name='manager-approval'),
    path('runs/<int:pk>/', PayrollRunDetailView.as_view(), name='run-detail'),
    path('entries/<int:pk>/edit/', PayrollEntryUpdateView.as_view(), name='entry-update'),
]
