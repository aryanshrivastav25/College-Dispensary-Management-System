
from django import forms


class DispenseForm(forms.Form):
    """Confirm a pharmacist-reviewed medicine handoff."""

    confirm_dispense = forms.BooleanField(
        label='I confirm the prescribed medicines are ready for handoff.',
    )
