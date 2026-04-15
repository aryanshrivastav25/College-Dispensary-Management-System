from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from appointments.models import Slot, Token
from consultation.models import DoctorProfile, Prescription, PrescriptionMedicine
from inventory.models import Medicine, Stock
from pharmacy.models import DispenseRecord

User = get_user_model()


class AccountsFlowTests(TestCase):
    """Regression tests for registration, profile setup, and dashboards."""

    def test_profile_is_created_for_standard_user(self):
        user = User.objects.create_user(username='student1', password='safe-pass-123')

        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.role, UserProfile.Role.STUDENT)

    def test_profile_is_created_for_superuser_as_admin(self):
        user = User.objects.create_superuser(
            username='admin1',
            email='admin@example.com',
            password='safe-pass-123',
        )

        self.assertEqual(user.profile.role, UserProfile.Role.ADMIN)

    def test_registration_creates_account_and_logs_user_in(self):
        response = self.client.post(
            reverse('accounts:register'),
            data={
                'username': 'alice',
                'first_name': 'Alice',
                'last_name': 'Avery',
                'email': 'alice@example.com',
                'role': UserProfile.Role.STUDENT,
                'roll_number': 'cs-101',
                'phone': '1234567890',
                'year_of_study': 2,
                'password1': 'VerySafePass123',
                'password2': 'VerySafePass123',
            },
        )

        self.assertRedirects(response, reverse('accounts:dashboard'))
        user = User.objects.get(username='alice')
        self.assertEqual(user.profile.roll_number, 'CS-101')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('accounts:dashboard'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:dashboard')}",
        )

    def test_doctor_dashboard_renders_operational_sections(self):
        user = User.objects.create_user(username='doctor1', password='safe-pass-123')
        user.profile.role = UserProfile.Role.DOCTOR
        user.profile.save(update_fields=['role'])
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:dashboard'))

        self.assertContains(response, 'Doctor workspace')
        self.assertContains(response, 'Waiting patients')
        self.assertContains(response, 'Doctor profile')

    def test_student_dashboard_shows_live_token_and_medicine_dosage_history(self):
        student = User.objects.create_user(username='student-dashboard', password='safe-pass-123')
        doctor = self._create_doctor_user('doctor-dashboard')
        doctor_profile = DoctorProfile.objects.create(user=doctor, specialization='General Practice')
        slot = Slot.objects.create(
            title='General Consultation',
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(hour=10, minute=0),
            end_time=time(hour=10, minute=30),
            max_capacity=5,
        )
        token = Token.objects.create(
            slot=slot,
            student=student.profile,
            qr_image='demo-qr',
            expires_at=timezone.now() + timedelta(hours=2),
        )
        prescription = Prescription.objects.create(
            token=token,
            doctor=doctor_profile,
            symptoms='Cough and fever',
        )
        PrescriptionMedicine.objects.create(
            prescription=prescription,
            medicine_name='Paracetamol',
            dosage_instructions='Take after meals twice daily',
            quantity=6,
        )
        DispenseRecord.objects.create(
            prescription=prescription,
            pharmacist=self._create_pharmacist_profile('pharma-student-history'),
            quota_signed=True,
        )
        self.client.force_login(student)

        response = self.client.get(reverse('accounts:dashboard'))

        self.assertContains(response, 'Live queue status')
        self.assertContains(response, str(token.token_code))
        self.assertContains(response, 'Recent medicines and dosages')
        self.assertContains(response, 'Take after meals twice daily')

    def test_pharmacist_dashboard_shows_pending_queue_and_low_stock(self):
        pharmacist = self._create_pharmacist_user('pharma-dashboard')
        student = User.objects.create_user(username='queue-student', password='safe-pass-123')
        doctor = self._create_doctor_user('queue-doctor')
        doctor_profile = DoctorProfile.objects.create(user=doctor, specialization='General Practice')
        slot = Slot.objects.create(
            title='Acute Visit',
            date=timezone.localdate(),
            start_time=time(hour=9, minute=0),
            end_time=time(hour=9, minute=30),
            max_capacity=5,
        )
        token = Token.objects.create(
            slot=slot,
            student=student.profile,
            qr_image='demo-qr',
            expires_at=timezone.now() + timedelta(hours=2),
            status=Token.Status.DONE,
        )
        prescription = Prescription.objects.create(
            token=token,
            doctor=doctor_profile,
            symptoms='Headache',
        )
        PrescriptionMedicine.objects.create(
            prescription=prescription,
            medicine_name='Ibuprofen',
            dosage_instructions='One tablet after food',
            quantity=3,
        )
        medicine = Medicine.objects.create(name='ORS')
        Stock.objects.create(medicine=medicine, quantity=1)
        self.client.force_login(pharmacist)

        response = self.client.get(reverse('accounts:dashboard'))

        self.assertContains(response, 'Ready to dispense')
        self.assertContains(response, 'Low-stock watch')
        self.assertContains(response, 'Ibuprofen')
        self.assertContains(response, 'ORS')

    def test_admin_dashboard_shows_operational_metrics(self):
        admin = User.objects.create_superuser(
            username='admin-dashboard',
            email='admin-dashboard@example.com',
            password='safe-pass-123',
        )
        doctor = self._create_doctor_user('admin-doctor')
        DoctorProfile.objects.create(user=doctor, specialization='General Practice', is_available=True)
        self.client.force_login(admin)

        response = self.client.get(reverse('accounts:dashboard'))

        self.assertContains(response, 'Doctors available')
        self.assertContains(response, 'Available doctors')
        self.assertContains(response, 'Pending pharmacy queue')

    def _create_doctor_user(self, username: str):
        doctor = User.objects.create_user(username=username, password='safe-pass-123')
        doctor.profile.role = UserProfile.Role.DOCTOR
        doctor.profile.save(update_fields=['role'])
        return doctor

    def _create_pharmacist_user(self, username: str):
        pharmacist = User.objects.create_user(username=username, password='safe-pass-123')
        pharmacist.profile.role = UserProfile.Role.PHARMACIST
        pharmacist.profile.save(update_fields=['role'])
        return pharmacist

    def _create_pharmacist_profile(self, username: str):
        return self._create_pharmacist_user(username).profile
