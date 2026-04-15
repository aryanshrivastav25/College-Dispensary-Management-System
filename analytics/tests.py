# campuscare/analytics/tests.py — Step 10
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from appointments.models import Slot, Token
from consultation.models import DoctorProfile, Prescription, PrescriptionMedicine
from inventory.models import Medicine, Stock
from pharmacy.models import DispenseRecord

User = get_user_model()


class AnalyticsFlowTests(TestCase):
    """Regression tests for triage, ETA, and history analytics views."""

    def setUp(self):
        self.student_user = User.objects.create_user(username='analytics-student', password='safe-pass-123')
        self.doctor_user = User.objects.create_user(username='analytics-doctor', password='safe-pass-123')
        self.pharmacist_user = User.objects.create_user(username='analytics-pharmacist', password='safe-pass-123')
        self.admin_user = User.objects.create_superuser(
            username='analytics-admin',
            email='analytics-admin@example.com',
            password='safe-pass-123',
        )
        self.doctor_user.profile.role = UserProfile.Role.DOCTOR
        self.doctor_user.profile.save(update_fields=['role'])
        self.pharmacist_user.profile.role = UserProfile.Role.PHARMACIST
        self.pharmacist_user.profile.save(update_fields=['role'])

        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Medicine',
        )
        self.slot = Slot.objects.create(
            title='Analytics Consultation',
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(hour=10, minute=0),
            end_time=time(hour=10, minute=30),
            max_capacity=3,
        )
        self.first_token = Token.objects.create(
            slot=self.slot,
            student=User.objects.create_user(username='queue-ahead', password='safe-pass-123').profile,
            qr_image='encoded-qr',
            expires_at=self.slot.starts_at + timedelta(minutes=15),
            status=Token.Status.WAITING,
        )
        self.student_token = Token.objects.create(
            slot=self.slot,
            student=self.student_user.profile,
            qr_image='encoded-qr',
            expires_at=self.slot.starts_at + timedelta(minutes=15),
            status=Token.Status.WAITING,
        )
        self.prescription = Prescription.objects.create(
            token=self.student_token,
            doctor=self.doctor_profile,
            symptoms='Cough and sore throat',
        )
        PrescriptionMedicine.objects.create(
            prescription=self.prescription,
            medicine_name='Cough Syrup',
            dosage_instructions='Two teaspoons twice daily',
            quantity=1,
        )
        self.dispense_record = DispenseRecord.objects.create(
            prescription=self.prescription,
            pharmacist=self.pharmacist_user.profile,
            quota_signed=True,
        )
        self.stock = Stock.objects.create(
            medicine=Medicine.objects.create(
                name='Cough Syrup',
                category=Medicine.Category.GENERAL,
                unit=Medicine.Unit.BOTTLE,
                description='Syrup used in analytics tests',
            ),
            quantity=2,
            season_tag=Stock.SeasonTag.WINTER,
        )

    def test_student_receives_triage_suggestion(self):
        self.client.force_login(self.student_user)

        response = self.client.post(
            reverse('analytics:triage'),
            data={'symptoms': 'I have a cough and mild fever since yesterday.'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'General Medicine')
        self.assertContains(response, 'routine')

    def test_eta_view_shows_queue_estimate(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse('analytics:eta'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '7 minutes')
        self.assertContains(response, 'Waiting')

    def test_history_view_shows_dispensed_medicines(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse('analytics:history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cough Syrup')
        self.assertContains(response, str(self.dispense_record.receipt_code))

    def test_non_student_cannot_access_triage(self):
        self.client.force_login(self.pharmacist_user)

        response = self.client.get(reverse('analytics:triage'))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_view_prediction_panel_after_training(self):
        call_command('train_predictor')
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('analytics:predict'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock prediction panel')
        self.assertContains(response, 'Cough Syrup')
