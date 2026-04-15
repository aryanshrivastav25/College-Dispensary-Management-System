
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import UserProfile
from appointments.models import Token
from consultation.models import Prescription
from core.constants import MONTHLY_MEDICINE_QUOTA
from pharmacy.models import DispenseRecord


def check_quota(student: UserProfile) -> dict[str, int | bool]:
    """Return the student's current monthly dispensing quota state."""
    month_start = timezone.localdate().replace(day=1)
    month_start_at = timezone.make_aware(
        datetime.combine(month_start, datetime.min.time())
    )
    used_quota = DispenseRecord.objects.filter(
        prescription__token__student=student,
        dispensed_at__gte=month_start_at,
    ).count()
    remaining_quota = max(MONTHLY_MEDICINE_QUOTA - used_quota, 0)
    return {
        'eligible': used_quota < MONTHLY_MEDICINE_QUOTA,
        'used_quota': used_quota,
        'remaining_quota': remaining_quota,
        'monthly_limit': MONTHLY_MEDICINE_QUOTA,
    }


def pending_dispense_queue() -> QuerySet[Prescription]:
    """Return prescriptions waiting for pharmacist fulfillment."""
    return (
        Prescription.objects.filter(token__status=Token.Status.DONE, dispense_record__isnull=True)
        .select_related('token__student__user', 'doctor__user')
        .prefetch_related('medicines')
        .order_by('created_at')
    )


@transaction.atomic
def generate_receipt(prescription: Prescription, pharmacist: UserProfile) -> DispenseRecord:
    """Create a dispense record after validating pharmacist role and student quota."""
    if pharmacist.role != UserProfile.Role.PHARMACIST:
        raise ValidationError('Only pharmacists can dispense medicines.')

    prescription = (
        Prescription.objects.select_for_update()
        .select_related('token__student__user', 'doctor__user')
        .prefetch_related('medicines')
        .get(pk=prescription.pk)
    )

    if hasattr(prescription, 'dispense_record'):
        raise ValidationError('This prescription has already been dispensed.')
    if not prescription.medicines.exists():
        raise ValidationError('This prescription has no medicines to dispense.')

    quota = check_quota(prescription.token.student)
    if not quota['eligible']:
        raise ValidationError('This student has reached the monthly medicine quota.')

    return DispenseRecord.objects.create(
        prescription=prescription,
        pharmacist=pharmacist,
        dispensed_at=timezone.now(),
        quota_signed=True,
    )
