
from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from appointments.models import Slot, Token
from consultation.models import DoctorProfile, Prescription, PrescriptionMedicine
from pharmacy.models import DispenseRecord

User = get_user_model()


class PharmacyFlowTests(TestCase):
    """Regression tests for dispensing and receipt workflows."""

    def setUp(self):
        self.student_user = User.objects.create_user(username='student-pharmacy', password='safe-pass-123')
        self.doctor_user = User.objects.create_user(username='doctor-pharmacy', password='safe-pass-123')
        self.pharmacist_user = User.objects.create_user(username='pharmacist-one', password='safe-pass-123')
        self.admin_user = User.objects.create_superuser(
            username='admin-pharmacy',
            email='admin@example.com',
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
            title='Follow-up Consultation',
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(hour=14, minute=0),
            end_time=time(hour=14, minute=30),
            max_capacity=2,
        )
        self.token = Token.objects.create(
            slot=self.slot,
            student=self.student_user.profile,
            qr_image='encoded-qr',
            expires_at=self.slot.starts_at + timedelta(minutes=15),
            status=Token.Status.DONE,
        )
        self.prescription = Prescription.objects.create(
            token=self.token,
            doctor=self.doctor_profile,
            symptoms='Seasonal cough',
        )
        self.medicine = PrescriptionMedicine.objects.create(
            prescription=self.prescription,
            medicine_name='Cough Syrup',
            dosage_instructions='Two teaspoons after meals',
            quantity=1,
        )

    def test_pharmacist_can_view_dispense_queue(self):
        self.client.force_login(self.pharmacist_user)

        response = self.client.get(reverse('pharmacy:queue'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Follow-up Consultation')
        self.assertContains(response, 'Dispense now')

    def test_dispense_creates_record_and_redirects_to_receipt(self):
        self.client.force_login(self.pharmacist_user)

        response = self.client.post(
            reverse('pharmacy:dispense', kwargs={'pk': self.prescription.pk}),
            data={'confirm_dispense': 'on'},
        )

        record = DispenseRecord.objects.get()
        self.assertRedirects(response, reverse('pharmacy:receipt', kwargs={'pk': record.pk}))
        self.assertTrue(record.quota_signed)
        self.assertEqual(record.pharmacist, self.pharmacist_user.profile)

    def test_dispense_is_blocked_when_quota_is_reached(self):
        previous_slot = Slot.objects.create(
            title='Earlier Consultation',
            date=timezone.localdate() + timedelta(days=2),
            start_time=time(hour=9, minute=0),
            end_time=time(hour=9, minute=30),
            max_capacity=2,
        )
        previous_token = Token.objects.create(
            slot=previous_slot,
            student=self.student_user.profile,
            qr_image='encoded-qr',
            expires_at=previous_slot.starts_at + timedelta(minutes=15),
            status=Token.Status.DONE,
        )
        previous_prescription = Prescription.objects.create(
            token=previous_token,
            doctor=self.doctor_profile,
            symptoms='Prior visit',
        )
        PrescriptionMedicine.objects.create(
            prescription=previous_prescription,
            medicine_name='Vitamin C',
            dosage_instructions='One tablet daily',
            quantity=10,
        )
        DispenseRecord.objects.create(
            prescription=previous_prescription,
            pharmacist=self.pharmacist_user.profile,
            quota_signed=True,
        )

        self.client.force_login(self.pharmacist_user)
        with patch('pharmacy.services.MONTHLY_MEDICINE_QUOTA', 1):
            response = self.client.post(
                reverse('pharmacy:dispense', kwargs={'pk': self.prescription.pk}),
                data={'confirm_dispense': 'on'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'monthly medicine quota')
        self.assertEqual(DispenseRecord.objects.filter(prescription=self.prescription).count(), 0)

    def test_admin_can_view_receipt(self):
        record = DispenseRecord.objects.create(
            prescription=self.prescription,
            pharmacist=self.pharmacist_user.profile,
            quota_signed=True,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('pharmacy:receipt', kwargs={'pk': record.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(record.receipt_code))

    def test_admin_can_review_but_cannot_submit_dispense(self):
        self.client.force_login(self.admin_user)

        get_response = self.client.get(reverse('pharmacy:dispense', kwargs={'pk': self.prescription.pk}))
        post_response = self.client.post(
            reverse('pharmacy:dispense', kwargs={'pk': self.prescription.pk}),
            data={'confirm_dispense': 'on'},
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(post_response.status_code, 403)
