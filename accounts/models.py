
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

User = get_user_model()


class UserProfile(models.Model):
    """Extended role and campus metadata for each authenticated user."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        DOCTOR = 'doctor', 'Doctor'
        PHARMACIST = 'pharmacist', 'Pharmacist'
        ADMIN = 'admin', 'Admin'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    roll_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    year_of_study = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        display_name = self.user.get_full_name() or self.user.username
        return f'{display_name} ({self.get_role_display()})'

    class Meta:
        ordering = ['user__username']
        verbose_name = 'User profile'
        verbose_name_plural = 'User profiles'