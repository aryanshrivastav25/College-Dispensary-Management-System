from django.utils import timezone

from analytics.services import eta_calculator, medicine_history
from appointments.models import Slot, Token
from appointments.services import get_active_token, slot_booking_note
from consultation.models import DoctorProfile, Prescription
from consultation.services import ensure_doctor_profile, waiting_queue
from inventory.services import low_stock_alert
from pharmacy.models import DispenseRecord
from pharmacy.services import check_quota, pending_dispense_queue


def build_student_dashboard(profile) -> dict[str, object]:
    """Return the dashboard context for a student user."""
    active_token = get_active_token(profile)
    token_eta = eta_calculator(active_token) if active_token else None
    quota = check_quota(profile)
    upcoming_slots = [
        {
            'slot': slot,
            'booking_note': slot_booking_note(slot),
        }
        for slot in Slot.objects.filter(date__gte=timezone.localdate()).order_by('date', 'start_time')[:3]
    ]

    return {
        'active_token': active_token,
        'token_eta': token_eta,
        'quota': quota,
        'upcoming_slots': upcoming_slots,
        'recent_prescriptions': list(
            Prescription.objects.filter(token__student=profile)
            .select_related('doctor__user', 'token__slot')
            .prefetch_related('medicines')
            .order_by('-created_at')[:3]
        ),
        'medicine_history': list(medicine_history(profile)[:3]),
        'metrics': [
            {
                'label': 'Queue ETA',
                'value': f"{token_eta['estimated_minutes']} min" if token_eta else 'No active token',
            },
            {
                'label': 'Quota left',
                'value': f"{quota['remaining_quota']} of {quota['monthly_limit']}",
            },
            {
                'label': 'Prescription records',
                'value': Prescription.objects.filter(token__student=profile).count(),
            },
        ],
    }


def build_doctor_dashboard(user) -> dict[str, object]:
    """Return the dashboard context for a doctor user."""
    doctor_profile = ensure_doctor_profile(user)
    today = timezone.localdate()
    return {
        'doctor_profile': doctor_profile,
        'waiting_tokens': list(waiting_queue()[:5]),
        'recent_prescriptions': list(
            Prescription.objects.filter(doctor=doctor_profile)
            .select_related('token__student__user', 'token__slot')
            .prefetch_related('medicines')
            .order_by('-created_at')[:4]
        ),
        'metrics': [
            {
                'label': 'Availability',
                'value': 'Available' if doctor_profile.is_available else 'Unavailable',
            },
            {
                'label': 'Patients waiting',
                'value': Token.objects.filter(status=Token.Status.WAITING).count(),
            },
            {
                'label': 'Prescriptions today',
                'value': Prescription.objects.filter(
                    doctor=doctor_profile,
                    created_at__date=today,
                ).count(),
            },
        ],
    }


def build_pharmacist_dashboard(profile) -> dict[str, object]:
    """Return the dashboard context for a pharmacist user."""
    today = timezone.localdate()
    return {
        'pending_prescriptions': list(pending_dispense_queue()[:5]),
        'low_stock_items': list(low_stock_alert()[:5]),
        'recent_dispense_records': list(
            DispenseRecord.objects.filter(pharmacist=profile)
            .select_related(
                'prescription__token__student__user',
                'prescription__doctor__user',
            )
            .prefetch_related('prescription__medicines')
            .order_by('-dispensed_at')[:4]
        ),
        'metrics': [
            {
                'label': 'Pending handoffs',
                'value': pending_dispense_queue().count(),
            },
            {
                'label': 'Low-stock alerts',
                'value': low_stock_alert().count(),
            },
            {
                'label': 'Dispensed this month',
                'value': DispenseRecord.objects.filter(
                    pharmacist=profile,
                    dispensed_at__date__month=today.month,
                    dispensed_at__date__year=today.year,
                ).count(),
            },
        ],
    }


def build_admin_dashboard() -> dict[str, object]:
    """Return the dashboard context for an admin user."""
    today = timezone.localdate()
    return {
        'available_doctors': DoctorProfile.objects.filter(is_available=True).select_related('user')[:4],
        'low_stock_items': list(low_stock_alert()[:5]),
        'pending_prescriptions': list(pending_dispense_queue()[:5]),
        'recent_dispense_records': list(
            DispenseRecord.objects.select_related(
                'pharmacist__user',
                'prescription__doctor__user',
                'prescription__token__student__user',
            )
            .prefetch_related('prescription__medicines')
            .order_by('-dispensed_at')[:4]
        ),
        'metrics': [
            {
                'label': 'Active queue',
                'value': Token.objects.filter(status__in=[Token.Status.WAITING, Token.Status.CALLED]).count(),
            },
            {
                'label': 'Pending pharmacy queue',
                'value': pending_dispense_queue().count(),
            },
            {
                'label': 'Doctors available',
                'value': DoctorProfile.objects.filter(is_available=True).count(),
            },
            {
                'label': 'Dispensed today',
                'value': DispenseRecord.objects.filter(dispensed_at__date=today).count(),
            },
        ],
    }
