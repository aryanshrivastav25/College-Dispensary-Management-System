# campuscare/core/management/commands/seed_demo_data.py
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from appointments.models import Slot, Token
from appointments.services import render_qr_image
from calendar_app.models import DispensarySchedule
from consultation.models import DoctorProfile, Prescription, PrescriptionMedicine
from inventory.models import Medicine, Stock
from pharmacy.models import DispenseRecord

User = get_user_model()


class Command(BaseCommand):
    """Seed the local database with realistic, rerunnable demo data."""

    help = 'Create demo users, schedules, inventory, appointments, prescriptions, and dispense records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--train-predictor',
            action='store_true',
            help='Train and persist the stock predictor after seeding the demo data.',
        )
        parser.add_argument(
            '--model-output',
            default=None,
            help='Optional path for the trained predictor artifact when --train-predictor is used.',
        )

    def handle(self, *args, **options):
        summary = self.seed_demo_data()
        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self.stdout.write(f"Users ensured: {summary['users']}")
        self.stdout.write(f"Schedules ensured: {summary['schedules']}")
        self.stdout.write(f"Inventory items ensured: {summary['stocks']}")
        self.stdout.write(f"Slots ensured: {summary['slots']}")
        self.stdout.write(f"Tokens ensured: {summary['tokens']}")
        self.stdout.write(f"Prescriptions ensured: {summary['prescriptions']}")
        self.stdout.write(f"Dispense records ensured: {summary['dispense_records']}")

        if options['train_predictor']:
            from ml.train import train_predictor

            training_summary = train_predictor(options['model_output'])
            self.stdout.write(self.style.SUCCESS('Stock predictor trained after seeding demo data.'))
            self.stdout.write(f"Saved model: {training_summary['model_path']}")
            self.stdout.write(f"Predictions generated: {training_summary['prediction_count']}")

    @transaction.atomic
    def seed_demo_data(self) -> dict[str, int]:
        """Create or update a consistent local demo dataset."""
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)

        users = {
            'admin': self.upsert_user(
                username='demo_admin',
                password='demo12345',
                role=UserProfile.Role.ADMIN,
                email='demo-admin@campuscare.local',
                first_name='Asha',
                last_name='Admin',
                is_staff=True,
                is_superuser=True,
            ),
            'doctor': self.upsert_user(
                username='demo_doctor',
                password='demo12345',
                role=UserProfile.Role.DOCTOR,
                email='demo-doctor@campuscare.local',
                first_name='Dev',
                last_name='Mehta',
            ),
            'pharmacist': self.upsert_user(
                username='demo_pharmacist',
                password='demo12345',
                role=UserProfile.Role.PHARMACIST,
                email='demo-pharmacist@campuscare.local',
                first_name='Riya',
                last_name='Shah',
            ),
            'student_demo': self.upsert_user(
                username='demo_student',
                password='demo12345',
                role=UserProfile.Role.STUDENT,
                email='demo-student@campuscare.local',
                first_name='Anika',
                last_name='Verma',
                roll_number='CC2026-001',
                phone='9876500001',
                year_of_study=2,
            ),
            'student_ahead': self.upsert_user(
                username='demo_student_ahead',
                password='demo12345',
                role=UserProfile.Role.STUDENT,
                email='demo-student-ahead@campuscare.local',
                first_name='Rahul',
                last_name='Sen',
                roll_number='CC2026-002',
                phone='9876500002',
                year_of_study=3,
            ),
            'student_history': self.upsert_user(
                username='demo_student_history',
                password='demo12345',
                role=UserProfile.Role.STUDENT,
                email='demo-student-history@campuscare.local',
                first_name='Maya',
                last_name='Das',
                roll_number='CC2026-003',
                phone='9876500003',
                year_of_study=1,
            ),
            'student_returning': self.upsert_user(
                username='demo_student_returning',
                password='demo12345',
                role=UserProfile.Role.STUDENT,
                email='demo-student-returning@campuscare.local',
                first_name='Karan',
                last_name='Roy',
                roll_number='CC2026-004',
                phone='9876500004',
                year_of_study=4,
            ),
            'student_pending': self.upsert_user(
                username='demo_student_pending',
                password='demo12345',
                role=UserProfile.Role.STUDENT,
                email='demo-student-pending@campuscare.local',
                first_name='Sara',
                last_name='Nair',
                roll_number='CC2026-005',
                phone='9876500005',
                year_of_study=2,
            ),
        }

        doctor_profile, _ = DoctorProfile.objects.get_or_create(
            user=users['doctor'],
            defaults={
                'specialization': 'General Medicine',
                'is_available': True,
            },
        )
        if doctor_profile.specialization != 'General Medicine' or not doctor_profile.is_available:
            doctor_profile.specialization = 'General Medicine'
            doctor_profile.is_available = True
            doctor_profile.save(update_fields=['specialization', 'is_available', 'updated_at'])

        schedules = [
            self.upsert_schedule(
                date=tomorrow,
                is_open=True,
                open_time=time(hour=9, minute=0),
                close_time=time(hour=17, minute=0),
                note='Regular weekday clinic hours.',
            ),
            self.upsert_schedule(
                date=day_after,
                is_open=True,
                open_time=time(hour=9, minute=30),
                close_time=time(hour=16, minute=30),
                note='Reduced staffing after lunch.',
            ),
            self.upsert_schedule(
                date=day_after + timedelta(days=1),
                is_open=False,
                note='Campus event closure.',
            ),
        ]

        inventory_items = [
            self.upsert_stock(
                name='Paracetamol',
                category=Medicine.Category.ANALGESIC,
                unit=Medicine.Unit.TABLET,
                description='Standard fever and pain relief tablets.',
                quantity=22,
                season_tag=Stock.SeasonTag.WINTER,
            ),
            self.upsert_stock(
                name='Cough Syrup',
                category=Medicine.Category.GENERAL,
                unit=Medicine.Unit.BOTTLE,
                description='Soothing syrup for cough and throat irritation.',
                quantity=6,
                season_tag=Stock.SeasonTag.MONSOON,
            ),
            self.upsert_stock(
                name='Cetirizine',
                category=Medicine.Category.GENERAL,
                unit=Medicine.Unit.TABLET,
                description='Anti-allergy tablets for seasonal irritation.',
                quantity=4,
                season_tag=Stock.SeasonTag.MONSOON,
            ),
            self.upsert_stock(
                name='ORS Sachet',
                category=Medicine.Category.SUPPLEMENT,
                unit=Medicine.Unit.BOX,
                description='Hydration support sachets for heat and stomach issues.',
                quantity=14,
                season_tag=Stock.SeasonTag.SUMMER,
            ),
            self.upsert_stock(
                name='Bandage Roll',
                category=Medicine.Category.FIRST_AID,
                unit=Medicine.Unit.BOX,
                description='Sterile dressing rolls for first aid care.',
                quantity=9,
                season_tag=Stock.SeasonTag.GENERAL,
            ),
        ]

        slots = {
            'morning_queue': self.upsert_slot(
                title='General Consultation Queue',
                date=tomorrow,
                start_time=time(hour=9, minute=30),
                end_time=time(hour=10, minute=0),
                max_capacity=5,
                notes='Queue demo with one student ahead and one student waiting.',
            ),
            'history_recent': self.upsert_slot(
                title='Recent Respiratory Follow-up',
                date=today - timedelta(days=10),
                start_time=time(hour=11, minute=0),
                end_time=time(hour=11, minute=30),
                max_capacity=3,
                notes='Recent completed consultation for history demo.',
            ),
            'history_older': self.upsert_slot(
                title='Seasonal Recovery Review',
                date=today - timedelta(days=45),
                start_time=time(hour=14, minute=0),
                end_time=time(hour=14, minute=30),
                max_capacity=3,
                notes='Older completed consultation for forecasting history.',
            ),
            'pending_dispense': self.upsert_slot(
                title='Pharmacy Handoff Pending',
                date=today,
                start_time=time(hour=16, minute=0),
                end_time=time(hour=16, minute=30),
                max_capacity=3,
                notes='Completed consultation waiting in the pharmacy queue.',
            ),
        }

        self.upsert_token(
            slot=slots['morning_queue'],
            student=users['student_ahead'].profile,
            status=Token.Status.WAITING,
            expires_at=timezone.now() + timedelta(hours=4),
        )
        self.upsert_token(
            slot=slots['morning_queue'],
            student=users['student_demo'].profile,
            status=Token.Status.WAITING,
            expires_at=timezone.now() + timedelta(hours=4, minutes=15),
        )
        recent_done = self.upsert_token(
            slot=slots['history_recent'],
            student=users['student_history'].profile,
            status=Token.Status.DONE,
            expires_at=timezone.now() + timedelta(hours=3),
        )
        older_done = self.upsert_token(
            slot=slots['history_older'],
            student=users['student_returning'].profile,
            status=Token.Status.DONE,
            expires_at=timezone.now() + timedelta(hours=3, minutes=30),
        )
        pending_done = self.upsert_token(
            slot=slots['pending_dispense'],
            student=users['student_pending'].profile,
            status=Token.Status.DONE,
            expires_at=timezone.now() + timedelta(hours=2),
        )

        recent_prescription = self.upsert_prescription(
            token=recent_done,
            doctor_profile=doctor_profile,
            symptoms='Persistent cough, mild fever, and throat irritation after a hostel cold outbreak.',
            medicines=[
                {
                    'medicine_name': 'Cough Syrup',
                    'dosage_instructions': 'Two teaspoons twice daily after meals',
                    'quantity': 1,
                },
                {
                    'medicine_name': 'Paracetamol',
                    'dosage_instructions': 'One tablet after meals for fever or body ache',
                    'quantity': 6,
                },
            ],
        )
        older_prescription = self.upsert_prescription(
            token=older_done,
            doctor_profile=doctor_profile,
            symptoms='Allergy flare-up with sneezing, watery eyes, and mild dehydration after travel.',
            medicines=[
                {
                    'medicine_name': 'Cetirizine',
                    'dosage_instructions': 'One tablet at bedtime for five days',
                    'quantity': 5,
                },
                {
                    'medicine_name': 'ORS Sachet',
                    'dosage_instructions': 'Mix one sachet in water and sip during the day',
                    'quantity': 3,
                },
            ],
        )
        pending_prescription = self.upsert_prescription(
            token=pending_done,
            doctor_profile=doctor_profile,
            symptoms='Headache and seasonal fatigue after back-to-back classes.',
            medicines=[
                {
                    'medicine_name': 'Paracetamol',
                    'dosage_instructions': 'One tablet after lunch and dinner for two days',
                    'quantity': 4,
                }
            ],
        )

        dispense_recent = self.upsert_dispense_record(
            prescription=recent_prescription,
            pharmacist=users['pharmacist'].profile,
        )
        dispense_older = self.upsert_dispense_record(
            prescription=older_prescription,
            pharmacist=users['pharmacist'].profile,
        )

        self.backdate_consultation_flow(
            token=recent_done,
            prescription=recent_prescription,
            dispense_record=dispense_recent,
            slot_date=today - timedelta(days=10),
            start_time=slots['history_recent'].start_time,
        )
        self.backdate_consultation_flow(
            token=older_done,
            prescription=older_prescription,
            dispense_record=dispense_older,
            slot_date=today - timedelta(days=45),
            start_time=slots['history_older'].start_time,
        )

        return {
            'users': len(users),
            'schedules': len(schedules),
            'stocks': len(inventory_items),
            'slots': len(slots),
            'tokens': 5,
            'prescriptions': 3,
            'dispense_records': 2,
        }

    def upsert_user(
        self,
        *,
        username: str,
        password: str,
        role: str,
        email: str,
        first_name: str,
        last_name: str,
        is_staff: bool = False,
        is_superuser: bool = False,
        roll_number: str | None = None,
        phone: str = '',
        year_of_study: int | None = None,
    ):
        """Create or update a demo user with stable credentials."""
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
            },
        )
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = is_staff or is_superuser
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()

        profile = user.profile
        profile.role = role
        profile.roll_number = roll_number
        profile.phone = phone
        profile.year_of_study = year_of_study
        profile.save(update_fields=['role', 'roll_number', 'phone', 'year_of_study', 'updated_at'])
        return user

    def upsert_schedule(
        self,
        *,
        date,
        is_open: bool,
        note: str,
        open_time: time | None = None,
        close_time: time | None = None,
    ) -> DispensarySchedule:
        """Create or update a demo dispensary schedule entry."""
        schedule, _ = DispensarySchedule.objects.get_or_create(
            date=date,
            defaults={
                'is_open': is_open,
                'open_time': open_time,
                'close_time': close_time,
                'note': note,
            },
        )
        schedule.is_open = is_open
        schedule.open_time = open_time
        schedule.close_time = close_time
        schedule.note = note
        schedule.save()
        return schedule

    def upsert_stock(
        self,
        *,
        name: str,
        category: str,
        unit: str,
        description: str,
        quantity: int,
        season_tag: str,
    ) -> Stock:
        """Create or update one inventory medicine and stock pair."""
        medicine, _ = Medicine.objects.get_or_create(name=name)
        medicine.category = category
        medicine.unit = unit
        medicine.description = description
        medicine.save()

        stock, _ = Stock.objects.get_or_create(medicine=medicine)
        stock.quantity = quantity
        stock.season_tag = season_tag
        stock.save()
        return stock

    def upsert_slot(
        self,
        *,
        title: str,
        date,
        start_time: time,
        end_time: time,
        max_capacity: int,
        notes: str,
    ) -> Slot:
        """Create or update one demo appointment slot."""
        slot, _ = Slot.objects.get_or_create(
            title=title,
            date=date,
            start_time=start_time,
            end_time=end_time,
            defaults={
                'max_capacity': max_capacity,
                'notes': notes,
            },
        )
        slot.max_capacity = max_capacity
        slot.notes = notes
        slot.save()
        return slot

    def upsert_token(
        self,
        *,
        slot: Slot,
        student: UserProfile,
        status: str,
        expires_at,
    ) -> Token:
        """Create or update one demo token and ensure a QR image exists."""
        token, created = Token.objects.get_or_create(
            slot=slot,
            student=student,
            defaults={
                'status': status,
                'expires_at': expires_at,
                'qr_image': 'pending',
            },
        )
        token.status = status
        token.expires_at = expires_at
        token.qr_image = render_qr_image(token)
        token.save()
        return token

    def upsert_prescription(
        self,
        *,
        token: Token,
        doctor_profile: DoctorProfile,
        symptoms: str,
        medicines: list[dict[str, object]],
    ) -> Prescription:
        """Create or update a demo prescription with medicine rows."""
        prescription, _ = Prescription.objects.get_or_create(
            token=token,
            defaults={
                'doctor': doctor_profile,
                'symptoms': symptoms,
            },
        )
        prescription.doctor = doctor_profile
        prescription.symptoms = symptoms
        prescription.save()

        prescription.medicines.all().delete()
        for medicine in medicines:
            PrescriptionMedicine.objects.create(
                prescription=prescription,
                medicine_name=medicine['medicine_name'],
                dosage_instructions=medicine['dosage_instructions'],
                quantity=medicine['quantity'],
            )
        return prescription

    def upsert_dispense_record(
        self,
        *,
        prescription: Prescription,
        pharmacist: UserProfile,
    ) -> DispenseRecord:
        """Create or update a dispense record for a demo prescription."""
        record, _ = DispenseRecord.objects.get_or_create(
            prescription=prescription,
            defaults={
                'pharmacist': pharmacist,
                'quota_signed': True,
            },
        )
        record.pharmacist = pharmacist
        record.quota_signed = True
        record.save()
        return record

    def backdate_consultation_flow(
        self,
        *,
        token: Token,
        prescription: Prescription,
        dispense_record: DispenseRecord,
        slot_date,
        start_time: time,
    ) -> None:
        """Backdate a completed flow so demo history looks realistic."""
        slot_start = timezone.make_aware(datetime.combine(slot_date, start_time))
        prescription_time = slot_start + timedelta(minutes=20)
        dispense_time = slot_start + timedelta(minutes=35)
        token.slot.date = slot_date
        token.slot.save(update_fields=['date', 'updated_at'])

        Token.objects.filter(pk=token.pk).update(
            created_at=slot_start,
            updated_at=dispense_time,
            expires_at=slot_start + timedelta(hours=1),
        )
        Prescription.objects.filter(pk=prescription.pk).update(
            created_at=prescription_time,
            updated_at=prescription_time,
        )
        DispenseRecord.objects.filter(pk=dispense_record.pk).update(
            dispensed_at=dispense_time,
            created_at=dispense_time,
            updated_at=dispense_time,
        )
