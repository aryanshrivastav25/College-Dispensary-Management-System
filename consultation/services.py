
from django.core.exceptions import ValidationError
from django.db import transaction

from appointments.models import Token
from appointments.services import expire_stale_tokens
from consultation.models import DoctorProfile, Prescription, PrescriptionMedicine


def ensure_doctor_profile(user) -> DoctorProfile:
    """Return the doctor's profile, creating a default one when needed."""
    expire_stale_tokens()
    profile = getattr(user, 'profile', None)
    if profile is None or profile.role != profile.Role.DOCTOR:
        raise ValidationError('Only doctor accounts can access consultation tools.')

    doctor_profile, _ = DoctorProfile.objects.get_or_create(
        user=user,
        defaults={'specialization': 'General Practice'},
    )
    return doctor_profile


def toggle_doctor_availability(user) -> DoctorProfile:
    """Flip the doctor's availability flag and persist it."""
    doctor_profile = ensure_doctor_profile(user)
    doctor_profile.is_available = not doctor_profile.is_available
    doctor_profile.save(update_fields=['is_available', 'updated_at'])
    return doctor_profile


def waiting_queue():
    """Return the current waiting consultation queue."""
    expire_stale_tokens()
    return Token.objects.filter(status=Token.Status.WAITING).select_related('student__user', 'slot').order_by('created_at')


def doctor_listing():
    """Return the ordered list of doctor profiles for display."""
    return DoctorProfile.objects.select_related('user').order_by('-is_available', 'user__first_name', 'user__username')


def mark_token_called(token: Token) -> Token:
    """Move a waiting token into the called state when consultation begins."""
    expire_stale_tokens()
    if token.status == Token.Status.WAITING:
        token.status = Token.Status.CALLED
        token.save(update_fields=['status', 'updated_at'])
    return token


@transaction.atomic
def prescribe_for_token(token: Token, doctor_profile: DoctorProfile, symptoms: str, medicines: list[dict]) -> Prescription:
    """Create or update a prescription and mark the consultation complete."""
    expire_stale_tokens()
    token.refresh_from_db()
    if token.status == Token.Status.EXPIRED:
        raise ValidationError('Expired tokens cannot be prescribed.')

    prescription, _ = Prescription.objects.get_or_create(
        token=token,
        defaults={'doctor': doctor_profile, 'symptoms': symptoms},
    )
    prescription.doctor = doctor_profile
    prescription.symptoms = symptoms
    prescription.save()

    prescription.medicines.all().delete()
    for medicine in medicines:
        PrescriptionMedicine.objects.create(
            prescription=prescription,
            medicine_name=medicine['medicine'],
            dosage_instructions=medicine['dosage_instructions'],
            quantity=medicine['quantity'],
        )

    token.status = Token.Status.DONE
    token.save(update_fields=['status', 'updated_at'])
    return prescription
