from django.urls import path

from .views import PayrollEntryUpdateView, PayrollGenerateView, PayrollRunDetailView, PayrollRunListView

app_name = 'payroll'

urlpatterns = [
    path('', PayrollRunListView.as_view(), name='run-list'),
    path('generate/', PayrollGenerateView.as_view(), name='generate'),
    path('runs/<int:pk>/', PayrollRunDetailView.as_view(), name='run-detail'),
    path('entries/<int:pk>/edit/', PayrollEntryUpdateView.as_view(), name='entry-update'),
]
