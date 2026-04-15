
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView

from accounts.models import UserProfile
from inventory.models import Stock
from appointments.models import Token
from consultation.forms import PrescriptionForm, PrescriptionMedicineFormSet
from consultation.models import Prescription
from consultation.services import (
    doctor_listing,
    ensure_doctor_profile,
    mark_token_called,
    prescribe_for_token,
    toggle_doctor_availability,
    waiting_queue,
)
from core.decorators import RoleRequiredMixin, role_required


class DoctorListView(LoginRequiredMixin, TemplateView):
    """Display doctor availability and the current consultation queue."""

    template_name = 'consultation/doctor_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_profile = None
        can_view_queue = self.request.user.profile.role in {
            UserProfile.Role.DOCTOR,
            UserProfile.Role.ADMIN,
        }
        if self.request.user.profile.role == UserProfile.Role.DOCTOR:
            current_profile = ensure_doctor_profile(self.request.user)

        context.update(
            {
                'can_view_queue': can_view_queue,
                'current_doctor_profile': current_profile,
                'doctor_profiles': doctor_listing(),
                'waiting_tokens': waiting_queue() if can_view_queue else [],
            }
        )
        return context


@login_required
@require_POST
@role_required(UserProfile.Role.DOCTOR)
def toggle_availability_view(request):
    """Toggle the logged-in doctor's availability."""
    doctor_profile = toggle_doctor_availability(request.user)
    state = 'available' if doctor_profile.is_available else 'unavailable'
    messages.success(request, f'You are now marked as {state}.')
    return redirect('consultation:doctor_list')


class PrescriptionCreateView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Capture a prescription for a queued consultation token."""

    allowed_roles = (UserProfile.Role.DOCTOR,)
    template_name = 'consultation/prescription_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'token': self.token,
                'doctor_profile': self.doctor_profile,
                'stocks': Stock.objects.select_related('medicine').filter(quantity__gt=0),  # 👈 ADD THIS
                **kwargs,
            }
        )
        return context

    def get_token(self):
        if not hasattr(self, '_token'):
            self._token = get_object_or_404(
                Token.objects.select_related('student__user', 'slot'),
                pk=self.kwargs['token_id'],
            )
        return self._token

    def get_doctor_profile(self):
        if not hasattr(self, '_doctor_profile'):
            self._doctor_profile = ensure_doctor_profile(self.request.user)
        return self._doctor_profile

    def get_existing_prescription(self):
        return getattr(self.get_token(), 'prescription', None)

    def get(self, request, *args, **kwargs):
        self.token = self.get_token()
        self.doctor_profile = self.get_doctor_profile()
        mark_token_called(self.token)
        prescription_form, medicine_formset = self.build_forms()
        return render(
            request,
            self.template_name,
            self.get_context_data(
                prescription_form=prescription_form,
                medicine_formset=medicine_formset,
            ),
        )

    def post(self, request, *args, **kwargs):
        self.token = self.get_token()
        self.doctor_profile = self.get_doctor_profile()
        mark_token_called(self.token)
        prescription_form, medicine_formset = self.build_forms(data=request.POST)

        if prescription_form.is_valid() and medicine_formset.is_valid():
            medicines = [
                {
                    "medicine": cleaned_data["medicine_name"].medicine,  # 👈 THIS LINE HERE
                    "dosage_instructions": cleaned_data["dosage_instructions"],
                    "quantity": cleaned_data["quantity"],
                }
                for cleaned_data in medicine_formset.cleaned_data
                if cleaned_data and not cleaned_data.get('DELETE')
            ]

            try:
                prescription = prescribe_for_token(
                    token=self.token,
                    doctor_profile=self.doctor_profile,
                    symptoms=prescription_form.cleaned_data['symptoms'],
                    medicines=medicines,
                )
            except ValidationError as exc:
                prescription_form.add_error(None, exc.messages[0] if exc.messages else str(exc))
            else:
                messages.success(request, 'Prescription saved successfully.')
                return redirect(reverse('consultation:print', kwargs={'pk': prescription.pk}))

        return render(
            request,
            self.template_name,
            self.get_context_data(
                prescription_form=prescription_form,
                medicine_formset=medicine_formset,
            ),
        )

    def build_forms(self, data=None):
        existing_prescription = self.get_existing_prescription()
        prescription_form = PrescriptionForm(data=data, instance=existing_prescription, prefix='prescription')
        medicine_formset = PrescriptionMedicineFormSet(
            data=data,
            prefix='medicines',
            initial=[
                {
                    'medicine_name': medicine.medicine_name,
                    'dosage_instructions': medicine.dosage_instructions,
                    'quantity': medicine.quantity,
                }
                for medicine in existing_prescription.medicines.all()
            ] if existing_prescription else None,
        )
        return prescription_form, medicine_formset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'token': self.token,
                'doctor_profile': self.doctor_profile,
                **kwargs,
            }
        )
        return context


class PrescriptionPrintView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Render a printable prescription slip."""

    allowed_roles = (
        UserProfile.Role.STUDENT,
        UserProfile.Role.DOCTOR,
        UserProfile.Role.PHARMACIST,
        UserProfile.Role.ADMIN,
    )
    model = Prescription
    template_name = 'consultation/prescription_print.html'
    context_object_name = 'prescription'

    def get_object(self, queryset=None):
        prescription = super().get_object(queryset)
        if (
            self.request.user.profile.role == UserProfile.Role.STUDENT
            and prescription.token.student_id != self.request.user.profile.pk
        ):
            raise PermissionDenied('You cannot view another student prescription.')
        return prescription
