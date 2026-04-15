# campuscare/appointments/models.py — Step 5
import uuid
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import UserProfile


class Slot(models.Model):
    """Bookable appointment slot in the campus dispensary."""

    title = models.CharField(max_length=120)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_capacity = models.PositiveIntegerField(default=10)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        if self.end_time <= self.start_time:
            raise ValidationError('Slot end time must be later than the start time.')
        if self.max_capacity < 1:
            raise ValidationError('Slot capacity must be at least 1.')

    @property
    def booked_count(self) -> int:
        return self.tokens.exclude(status=Token.Status.EXPIRED).count()

    @property
    def remaining_capacity(self) -> int:
        return max(self.max_capacity - self.booked_count, 0)

    @property
    def starts_at(self):
        return timezone.make_aware(datetime.combine(self.date, self.start_time))

    @property
    def ends_at(self):
        return timezone.make_aware(datetime.combine(self.date, self.end_time))

    def __str__(self) -> str:
        return f'{self.title} on {self.date:%d %b %Y} at {self.start_time:%I:%M %p}'

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Slot'
        verbose_name_plural = 'Slots'


class Token(models.Model):
    """Queue token issued to a student after booking a slot."""

    class Status(models.TextChoices):
        WAITING = 'waiting', 'Waiting'
        CALLED = 'called', 'Called'
        DONE = 'done', 'Done'
        EXPIRED = 'expired', 'Expired'

    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name='tokens')
    student = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='tokens')
    token_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_image = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.WAITING)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        if self.student.role != UserProfile.Role.STUDENT:
            raise ValidationError('Only student profiles can hold appointment tokens.')
        if self.expires_at <= timezone.now() and self.status != self.Status.EXPIRED:
            raise ValidationError('Token expiry must be in the future when the token is active.')

    def __str__(self) -> str:
        return f'Token {self.token_code} for {self.student.user.username}'

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Token'
        verbose_name_plural = 'Tokens'
        constraints = [
            models.UniqueConstraint(fields=['slot', 'student'], name='unique_slot_booking_per_student'),
        ]
