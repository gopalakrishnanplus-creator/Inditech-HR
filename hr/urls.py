from django.urls import path

from .views import (
    ApprovedLeaveCreateView,
    ApprovedLeaveListView,
    ApprovedLeaveUpdateView,
    EmployeeContractCreateView,
    EmployeeContractListView,
    EmployeeContractUpdateView,
    EmployeeCreateView,
    EmployeeListView,
    EmployeeUpdateView,
    HolidayCreateView,
    HolidayListView,
    HolidayUpdateView,
)

app_name = 'hr'

urlpatterns = [
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/new/', EmployeeCreateView.as_view(), name='employee-create'),
    path('employees/<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee-update'),
    path('contracts/', EmployeeContractListView.as_view(), name='contract-list'),
    path('contracts/new/', EmployeeContractCreateView.as_view(), name='contract-create'),
    path('contracts/<int:pk>/edit/', EmployeeContractUpdateView.as_view(), name='contract-update'),
    path('holidays/', HolidayListView.as_view(), name='holiday-list'),
    path('holidays/new/', HolidayCreateView.as_view(), name='holiday-create'),
    path('holidays/<int:pk>/edit/', HolidayUpdateView.as_view(), name='holiday-update'),
    path('leaves/', ApprovedLeaveListView.as_view(), name='leave-list'),
    path('leaves/new/', ApprovedLeaveCreateView.as_view(), name='leave-create'),
    path('leaves/<int:pk>/edit/', ApprovedLeaveUpdateView.as_view(), name='leave-update'),
]
