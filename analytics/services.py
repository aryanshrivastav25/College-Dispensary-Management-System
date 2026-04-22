# campuscare/analytics/services.py — Step 9
import json
from pathlib import Path

from accounts.models import UserProfile
from appointments.models import Token
from appointments.services import get_queue_snapshot
from core.constants import AVG_CONSULT_MINUTES
from pharmacy.models import DispenseRecord

TRIAGE_RULES_PATH = Path(__file__).with_name('triage_rules.json')


def load_triage_rules() -> list[dict[str, object]]:
    """Load the local triage ruleset from the JSON config file."""
    with TRIAGE_RULES_PATH.open(encoding='utf-8') as rules_file:
        return json.load(rules_file)


def triage_suggest(symptoms: str) -> dict[str, object]:
    """Return the best triage suggestion for a symptom description."""
    normalized = symptoms.lower()
    rules = load_triage_rules()

    for rule in rules:
        if any(keyword in normalized for keyword in rule['keywords']):
            return {
                'doctor_type': rule['doctor_type'],
                'urgency': rule['urgency'],
                'message': rule['message'],
                'matched_keywords': [keyword for keyword in rule['keywords'] if keyword in normalized],
            }

    return {
        'doctor_type': 'General Practice',
        'urgency': 'routine',
        'message': 'Book a general consultation so the doctor can evaluate your symptoms in person.',
        'matched_keywords': [],
    }


def eta_calculator(token: Token) -> dict[str, int | str]:
    """Calculate the live queue ETA for a token."""
    snapshot = get_queue_snapshot(token)
    waiting_ahead = int(snapshot['waiting_ahead'])
    estimated_minutes = waiting_ahead * AVG_CONSULT_MINUTES
    return {
        **snapshot,
        'estimated_minutes': estimated_minutes,
        'status_label': str(snapshot['status']).replace('_', ' ').title(),
    }


def medicine_history(student: UserProfile):
    """Return the student's dispensed medicine history timeline."""
    return (
        DispenseRecord.objects.filter(prescription__token__student=student)
        .select_related('pharmacist__user', 'prescription__doctor__user')
        .prefetch_related('prescription__medicines')
        .order_by('-dispensed_at')
    )
