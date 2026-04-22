
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import UserProfile
from consultation.models import Prescription


class DispenseRecord(models.Model):
    """Receipt-backed record of a completed pharmacy handoff."""

    prescription = models.OneToOneField(
        Prescription,
        on_delete=models.CASCADE,
        related_name='dispense_record',
    )
    pharmacist = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name='dispense_records',
    )
    receipt_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    dispensed_at = models.DateTimeField(default=timezone.now)
    quota_signed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        if self.pharmacist_id and self.pharmacist.role != UserProfile.Role.PHARMACIST:
            raise ValidationError('Only pharmacist profiles can issue dispense records.')
        if self.prescription_id and not self.prescription.medicines.exists():
            raise ValidationError('A prescription must include at least one medicine before dispensing.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'Receipt {self.receipt_code} for {self.prescription.token.student.user.username}'

    class Meta:
        ordering = ['-dispensed_at']
        verbose_name = 'Dispense record'
        verbose_name_plural = 'Dispense records'
