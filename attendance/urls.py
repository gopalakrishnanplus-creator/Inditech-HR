from django.urls import path

from .views import AttendanceHistoryView, AttendanceSubmitView

app_name = 'attendance'

urlpatterns = [
    path('submit/', AttendanceSubmitView.as_view(), name='submit'),
    path('history/', AttendanceHistoryView.as_view(), name='history'),
]
