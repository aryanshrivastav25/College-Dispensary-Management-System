from django.core.exceptions import ValidationError
from django.db import models


class DispensarySchedule(models.Model):
    """Daily schedule record for the dispensary."""

    date = models.DateField(unique=True)
    is_open = models.BooleanField(default=True)
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        if self.is_open:
            if not self.open_time or not self.close_time:
                raise ValidationError('Open dispensary days must include opening and closing times.')
            if self.close_time <= self.open_time:
                raise ValidationError('Closing time must be later than opening time.')
        else:
            self.open_time = None
            self.close_time = None

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        state = 'Open' if self.is_open else 'Closed'
        return f'{self.date:%d %b %Y} ({state})'

    class Meta:
        ordering = ['date']
        verbose_name = 'Dispensary schedule'
        verbose_name_plural = 'Dispensary schedules'
