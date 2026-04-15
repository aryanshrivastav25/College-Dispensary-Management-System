# campuscare/appointments/admin.py — Step 5
from django.contrib import admin

from appointments.models import Slot, Token


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    """Admin configuration for appointment slots."""

    list_display = ('title', 'date', 'start_time', 'end_time', 'max_capacity')
    list_filter = ('date',)
    search_fields = ('title', 'notes')
    ordering = ('date', 'start_time')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    """Admin configuration for appointment tokens."""

    list_display = ('token_code', 'student', 'slot', 'status', 'expires_at')
    list_filter = ('status', 'slot__date')
    search_fields = ('token_code', 'student__user__username', 'student__roll_number', 'slot__title')
    ordering = ('created_at',)
