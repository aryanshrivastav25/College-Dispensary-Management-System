from django import forms

from calendar_app.models import DispensarySchedule


class DispensaryScheduleForm(forms.ModelForm):
    """Create or update a daily dispensary schedule entry."""

    class Meta:
        model = DispensarySchedule
        fields = ('date', 'is_open', 'open_time', 'close_time', 'note')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'open_time': forms.TimeInput(attrs={'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'type': 'time'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self) -> dict:
        cleaned_data = super().clean()
        if not cleaned_data.get('is_open'):
            cleaned_data['open_time'] = None
            cleaned_data['close_time'] = None
        return cleaned_data
