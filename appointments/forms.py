from django import forms

from appointments.models import Slot


class SlotBookingForm(forms.Form):
    """Confirm that the student wants to book the selected slot."""

    confirm_booking = forms.BooleanField(
        label='I confirm that I will arrive on time for this appointment slot.',
        required=True,
    )


class SlotCreateForm(forms.ModelForm):
    """Create a slot directly from the appointments page for admins."""

    class Meta:
        model = Slot
        fields = ('title', 'date', 'start_time', 'end_time', 'max_capacity', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
