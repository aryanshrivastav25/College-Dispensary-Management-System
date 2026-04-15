
from django.contrib import admin

from inventory.models import Medicine, Stock


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    """Admin configuration for medicine catalog items."""

    list_display = ('name', 'category', 'unit', 'updated_at')
    list_filter = ('category', 'unit')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Admin configuration for stock levels."""

    list_display = ('medicine', 'quantity', 'season_tag', 'updated_at')
    list_filter = ('season_tag',)
    search_fields = ('medicine__name',)
    ordering = ('quantity', 'medicine__name')
