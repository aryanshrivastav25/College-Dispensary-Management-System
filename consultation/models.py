
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import UserProfile
from appointments.models import Token

User = get_user_model()


class DoctorProfile(models.Model):
    """Availability and specialization details for a doctor user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=120, default='General Practice')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        if not self.user_id:
            return
        profile = getattr(self.user, 'profile', None)
        if profile is None or profile.role != UserProfile.Role.DOCTOR:
            raise ValidationError('Doctor profiles can only be attached to users with the doctor role.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Dr. {self.user.get_full_name() or self.user.username}"

    class Meta:
        ordering = ['user__first_name', 'user__username']
        verbose_name = 'Doctor profile'
        verbose_name_plural = 'Doctor profiles'


class Prescription(models.Model):
    """Doctor-authored prescription for a booked appointment token."""

    token = models.OneToOneField(Token, on_delete=models.CASCADE, related_name='prescription')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.PROTECT, related_name='prescriptions')
    symptoms = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        if self.token_id and self.token.status == Token.Status.EXPIRED:
            raise ValidationError('Expired tokens cannot be prescribed.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'Prescription for {self.token.student.user.username}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'


class PrescriptionMedicine(models.Model):
    """Individual medicine rows attached to a prescription."""

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medicines')
    medicine_name = models.CharField(max_length=120)
    dosage_instructions = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.medicine_name} x {self.quantity}'

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Prescription medicine'
        verbose_name_plural = 'Prescription medicines'
