from django.urls import path

from calendar_app.views import CalendarMonthView, ScheduleManageView

app_name = 'calendar'

urlpatterns = [
    path('', CalendarMonthView.as_view(), name='month'),
    path('manage/', ScheduleManageView.as_view(), name='manage'),
]
