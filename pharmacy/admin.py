
from django.contrib import admin

from pharmacy.models import DispenseRecord


@admin.register(DispenseRecord)
class DispenseRecordAdmin(admin.ModelAdmin):
    """Admin configuration for pharmacy dispense records."""

    list_display = ('receipt_code', 'prescription', 'pharmacist', 'dispensed_at', 'quota_signed')
    list_filter = ('quota_signed', 'dispensed_at')
    search_fields = (
        'receipt_code',
        'prescription__token__student__user__username',
        'pharmacist__user__username',
    )
    ordering = ('-dispensed_at',)
