
from django.db import transaction
from django.db.models import QuerySet

from core.constants import LOW_STOCK_THRESHOLD
from inventory.models import Medicine, Stock


def stock_catalog() -> QuerySet[Stock]:
    """Return the inventory catalog with related medicine data."""
    return Stock.objects.select_related('medicine').order_by('medicine__name')


def low_stock_alert(threshold: int = LOW_STOCK_THRESHOLD) -> QuerySet[Stock]:
    """Return stock rows at or below the low-stock threshold."""
    return stock_catalog().filter(quantity__lte=threshold)


@transaction.atomic
def create_inventory_entry(medicine_data: dict, stock_data: dict) -> Stock:
    """Create a medicine and its corresponding stock record."""
    medicine = Medicine.objects.create(**medicine_data)
    return Stock.objects.create(medicine=medicine, **stock_data)


@transaction.atomic
def update_inventory_entry(stock: Stock, medicine_data: dict, stock_data: dict) -> Stock:
    """Update both the medicine catalog entry and live stock row."""
    for field, value in medicine_data.items():
        setattr(stock.medicine, field, value)
    stock.medicine.save()

    for field, value in stock_data.items():
        setattr(stock, field, value)
    stock.save()
    return stock
