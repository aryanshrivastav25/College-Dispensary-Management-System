
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import DetailView, TemplateView

from accounts.models import UserProfile
from consultation.models import Prescription
from core.decorators import RoleRequiredMixin
from pharmacy.forms import DispenseForm
from pharmacy.models import DispenseRecord
from pharmacy.services import check_quota, generate_receipt, pending_dispense_queue


class DispenseQueueView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Display the pending pharmacy queue."""

    allowed_roles = (UserProfile.Role.PHARMACIST, UserProfile.Role.ADMIN)
    template_name = 'pharmacy/dispense_queue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'pending_prescriptions': pending_dispense_queue(),
                **kwargs,
            }
        )
        return context


class DispensePrescriptionView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Review one prescription and complete dispensing."""

    allowed_roles = (UserProfile.Role.PHARMACIST, UserProfile.Role.ADMIN)
    template_name = 'pharmacy/dispense_queue.html'

    def get_prescription(self) -> Prescription:
        if not hasattr(self, '_prescription'):
            self._prescription = get_object_or_404(
                Prescription.objects.select_related('token__student__user', 'doctor__user')
                .prefetch_related('medicines'),
                pk=self.kwargs['pk'],
            )
        return self._prescription

    def get(self, request, *args, **kwargs):
        prescription = self.get_prescription()
        return render(
            request,
            self.template_name,
            self.get_context_data(
                selected_prescription=prescription,
                quota=check_quota(prescription.token.student),
                dispense_form=DispenseForm(),
            ),
        )

    def post(self, request, *args, **kwargs):
        if request.user.profile.role != UserProfile.Role.PHARMACIST:
            raise PermissionDenied

        prescription = self.get_prescription()
        dispense_form = DispenseForm(request.POST)

        if dispense_form.is_valid():
            try:
                record = generate_receipt(
                    prescription=prescription,
                    pharmacist=request.user.profile,
                )
            except ValidationError as exc:
                dispense_form.add_error(None, exc.messages[0] if exc.messages else str(exc))
            else:
                messages.success(request, 'Medicines dispensed and receipt generated.')
                return redirect(reverse('pharmacy:receipt', kwargs={'pk': record.pk}))

        return render(
            request,
            self.template_name,
            self.get_context_data(
                selected_prescription=prescription,
                quota=check_quota(prescription.token.student),
                dispense_form=dispense_form,
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'pending_prescriptions': pending_dispense_queue(),
                'can_dispense': self.request.user.profile.role == UserProfile.Role.PHARMACIST,
                **kwargs,
            }
        )
        return context


class ReceiptDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Render the printable pharmacy receipt."""

    allowed_roles = (UserProfile.Role.PHARMACIST, UserProfile.Role.ADMIN)
    model = DispenseRecord
    template_name = 'pharmacy/receipt.html'
    context_object_name = 'record'

    def get_queryset(self):
        return DispenseRecord.objects.select_related(
            'pharmacist__user',
            'prescription__doctor__user',
            'prescription__token__student__user',
        ).prefetch_related('prescription__medicines')
