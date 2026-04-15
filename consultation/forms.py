
from django import forms
from django.forms import formset_factory

from consultation.models import Prescription
from inventory.models import Stock


class PrescriptionForm(forms.ModelForm):
    """Capture the presenting symptoms for a consultation."""

    class Meta:
        model = Prescription
        fields = ('symptoms',)
        widgets = {
            'symptoms': forms.Textarea(attrs={'rows': 5}),
        }


# class PrescriptionMedicineForm(forms.Form):
#     """Capture one medicine row on a prescription."""

#     medicine_name = forms.CharField(max_length=120)
#     dosage_instructions = forms.CharField(max_length=255)
#     quantity = forms.IntegerField(min_value=1)

class PrescriptionMedicineForm(forms.Form):
    medicine_name = forms.ModelChoiceField(
        queryset=Stock.objects.select_related('medicine').filter(quantity__gt=0),
        empty_label="Select medicine",
        widget=forms.Select(attrs={"class": "form-control"})
    )
    quantity = forms.IntegerField(min_value=1)
    dosage_instructions = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom label
        self.fields["medicine_name"].label_from_instance = (
            lambda obj: f"{obj.medicine.name} ({obj.quantity} available)"
        )

PrescriptionMedicineFormSet = formset_factory(
    PrescriptionMedicineForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
