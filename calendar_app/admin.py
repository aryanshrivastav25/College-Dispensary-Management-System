from django.contrib import admin

from calendar_app.models import DispensarySchedule


@admin.register(DispensarySchedule)
class DispensaryScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for daily dispensary schedules."""

    list_display = ('date', 'is_open', 'open_time', 'close_time', 'note')
    list_filter = ('is_open', 'date')
    search_fields = ('note',)
    ordering = ('date',)
