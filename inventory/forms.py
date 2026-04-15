
from django import forms

from inventory.models import Medicine, Stock


class MedicineForm(forms.ModelForm):
    """Capture the medicine catalog details."""

    class Meta:
        model = Medicine
        fields = ('name', 'category', 'unit', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class StockForm(forms.ModelForm):
    """Capture the live stock details for a medicine."""

    class Meta:
        model = Stock
        fields = ('quantity', 'season_tag')
