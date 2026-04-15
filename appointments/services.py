# campuscare/appointments/services.py — Step 5
import base64
import io
import json
from datetime import datetime, timedelta

import qrcode
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from calendar_app.models import DispensarySchedule
from core.constants import SLOT_GRACE_MINUTES

from appointments.models import Slot, Token


class BookingError(ValidationError):
    """Raised when a slot cannot be booked."""


def build_token_expiry(slot: Slot) -> datetime:
    """Expire slot after its END time (not start time)."""
    slot_end = datetime.combine(slot.date, slot.end_time)

    if timezone.is_naive(slot_end):
        slot_end = timezone.make_aware(slot_end, timezone.get_current_timezone())

    return slot_end - timedelta(minutes=20)


def render_qr_image(token: Token) -> str:
    """Return a base64-encoded PNG QR image for a token."""
    payload = json.dumps(
        {
            'token_code': str(token.token_code),
            'student': token.student.user.username,
            'slot': token.slot.title,
            'date': token.slot.date.isoformat(),
            'start_time': token.slot.start_time.isoformat(),
        }
    )
    qr_image = qrcode.make(payload)
    buffer = io.BytesIO()
    qr_image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def slot_booking_note(slot: Slot, reference_time: datetime | None = None) -> str:
    """Describe whether a slot can currently be booked."""
    reference_time = reference_time or timezone.now()
    schedule = DispensarySchedule.objects.filter(date=slot.date).first()

    if schedule and not schedule.is_open:
        return 'This slot falls on a closed dispensary day.'
    if slot.remaining_capacity < 1:
        return 'This slot is already full.'
    if build_token_expiry(slot) <= reference_time:
        return 'This slot has already passed.'
    return 'Book this slot'


def is_slot_bookable(slot: Slot, reference_time: datetime | None = None) -> bool:
    """Return True when the slot can accept a new booking."""
    return slot_booking_note(slot, reference_time) == 'Book this slot'


def get_active_token(student: UserProfile) -> Token | None:
    """Return the student's current active token, if one exists."""
    expire_stale_tokens()
    return (
        Token.objects.filter(student=student, status__in=[Token.Status.WAITING, Token.Status.CALLED])
        .order_by('-created_at')
        .first()
    )


@transaction.atomic
def generate_token(student: UserProfile, slot: Slot) -> Token:
    """Create a QR-backed queue token for a student's booked slot."""
    if student.role != UserProfile.Role.STUDENT:
        raise BookingError('Only students can book appointment slots.')

    expire_stale_tokens()

    if get_active_token(student):
        raise BookingError('You already have an active appointment token.')

    slot = Slot.objects.select_for_update().get(pk=slot.pk)

    if not is_slot_bookable(slot):
        raise BookingError(slot_booking_note(slot))

    if Token.objects.filter(slot=slot, student=student).exists():
        raise BookingError('You have already booked this slot.')

    token = Token(
        slot=slot,
        student=student,
        expires_at=build_token_expiry(slot),
        qr_image='pending',
    )
    token.qr_image = render_qr_image(token)
    token.save()
    return token


def expire_stale_tokens(reference_time: datetime | None = None) -> int:
    """Expire any waiting or called tokens whose validity window has ended."""
    reference_time = reference_time or timezone.now()
    return Token.objects.filter(
        status__in=[Token.Status.WAITING, Token.Status.CALLED],
        expires_at__lt=reference_time,
    ).update(status=Token.Status.EXPIRED, updated_at=reference_time)

def delete_expired_slots(reference_time=None):
    reference_time = reference_time or timezone.now()

    slots = Slot.objects.all()
    deletable_ids = []

    for slot in slots:
        slot_end = datetime.combine(slot.date, slot.end_time)
        slot_end = timezone.make_aware(slot_end)

        if slot_end < reference_time - timedelta(hours=1):
            deletable_ids.append(slot.id)

    return Slot.objects.filter(id__in=deletable_ids).delete()[0]


def get_queue_snapshot(token: Token) -> dict[str, int | str]:
    """Return the student's live queue metrics for a token."""
    expire_stale_tokens()
    token.refresh_from_db()

    if token.status != Token.Status.WAITING:
        return {
            'status': token.status,
            'waiting_ahead': 0,
            'queue_position': 0,
        }

    waiting_tokens = list(
        token.slot.tokens.filter(status=Token.Status.WAITING).order_by('created_at', 'pk')
    )
    queue_position = next(
        (index for index, queued_token in enumerate(waiting_tokens, start=1) if queued_token.pk == token.pk),
        0,
    )
    waiting_ahead = max(queue_position - 1, 0)
    return {
        'status': token.status,
        'waiting_ahead': waiting_ahead,
        'queue_position': queue_position,
    }
