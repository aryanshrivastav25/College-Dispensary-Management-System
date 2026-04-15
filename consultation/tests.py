
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Slot, Token
from consultation.models import DoctorProfile, Prescription

User = get_user_model()


class ConsultationFlowTests(TestCase):
    """Regression tests for doctor availability and prescription flow."""

    def setUp(self):
        self.student_user = User.objects.create_user(username='patient-one', password='safe-pass-123')
        self.doctor_user = User.objects.create_user(username='doctor-one', password='safe-pass-123')
        self.doctor_user.profile.role = 'doctor'
        self.doctor_user.profile.save(update_fields=['role'])
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Medicine',
        )
        self.slot = Slot.objects.create(
            title='General Consultation',
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(hour=11, minute=0),
            end_time=time(hour=11, minute=30),
            max_capacity=3,
        )
        self.token = Token.objects.create(
            slot=self.slot,
            student=self.student_user.profile,
            qr_image='encoded-qr',
            expires_at=self.slot.starts_at + timedelta(minutes=10),
        )

    def test_doctor_can_toggle_availability(self):
        self.client.force_login(self.doctor_user)

        response = self.client.post(reverse('consultation:toggle_availability'))

        self.assertRedirects(response, reverse('consultation:doctor_list'))
        self.doctor_profile.refresh_from_db()
        self.assertFalse(self.doctor_profile.is_available)

    def test_prescribe_view_creates_prescription_and_marks_token_done(self):
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse('consultation:prescribe', kwargs={'token_id': self.token.pk}),
            data={
                'prescription-symptoms': 'Headache and mild fever',
                'medicines-TOTAL_FORMS': '1',
                'medicines-INITIAL_FORMS': '0',
                'medicines-MIN_NUM_FORMS': '1',
                'medicines-MAX_NUM_FORMS': '1000',
                'medicines-0-medicine_name': 'Paracetamol',
                'medicines-0-dosage_instructions': 'One tablet after meals',
                'medicines-0-quantity': '6',
            },
        )

        prescription = Prescription.objects.get()
        self.assertRedirects(response, reverse('consultation:print', kwargs={'pk': prescription.pk}))
        self.token.refresh_from_db()
        self.assertEqual(self.token.status, Token.Status.DONE)
        self.assertEqual(prescription.medicines.count(), 1)

    def test_student_can_view_own_printable_prescription(self):
        prescription = Prescription.objects.create(
            token=self.token,
            doctor=self.doctor_profile,
            symptoms='Headache',
        )
        self.client.force_login(self.student_user)

        response = self.client.get(reverse('consultation:print', kwargs={'pk': prescription.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Printable prescription')

    def test_student_cannot_view_queue_listing(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse('consultation:doctor_list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Waiting queue')
