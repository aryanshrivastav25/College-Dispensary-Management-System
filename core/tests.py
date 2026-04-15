from pathlib import Path

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from appointments.models import Slot, Token
from consultation.models import Prescription
from inventory.models import Stock
from pharmacy.models import DispenseRecord
from core.context_processors import dispensary_status

User = get_user_model()


class CoreTemplateUtilityTests(TestCase):
    """Regression tests for shared template utilities."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_if_role_renders_matching_branch(self):
        user = User.objects.create_user(username='doctor-role', password='safe-pass-123')
        user.profile.role = 'doctor'
        user.profile.save(update_fields=['role'])
        request = self.factory.get('/')
        request.user = user

        rendered = Template(
            "{% load role_tags %}{% if_role 'doctor' %}doctor-zone{% else %}nope{% endif_role %}"
        ).render(Context({'request': request}))

        self.assertEqual(rendered, 'doctor-zone')

    def test_if_role_renders_else_branch_for_mismatch(self):
        user = User.objects.create_user(username='student-role', password='safe-pass-123')
        request = self.factory.get('/')
        request.user = user

        rendered = Template(
            "{% load role_tags %}{% if_role 'doctor' %}doctor-zone{% else %}student-zone{% endif_role %}"
        ).render(Context({'request': request}))

        self.assertEqual(rendered, 'student-zone')

    def test_dispensary_status_returns_default_open_when_today_has_no_schedule(self):
        request = self.factory.get('/')

        context = dispensary_status(request)

        self.assertEqual(context['dispensary_status']['label'], 'Open today')
        self.assertTrue(context['dispensary_status']['is_open'])
        self.assertEqual(context['dispensary_status']['detail'], 'Default hours: 9:00 AM to 5:00 PM')


class DemoSeedCommandTests(TestCase):
    """Regression tests for the demo-data seeding command."""

    def test_seed_demo_data_is_idempotent(self):
        call_command('seed_demo_data')
        initial_counts = {
            'users': User.objects.filter(username__startswith='demo_').count(),
            'slots': Slot.objects.count(),
            'tokens': Token.objects.count(),
            'prescriptions': Prescription.objects.count(),
            'dispense_records': DispenseRecord.objects.count(),
            'stocks': Stock.objects.count(),
        }

        call_command('seed_demo_data')
        rerun_counts = {
            'users': User.objects.filter(username__startswith='demo_').count(),
            'slots': Slot.objects.count(),
            'tokens': Token.objects.count(),
            'prescriptions': Prescription.objects.count(),
            'dispense_records': DispenseRecord.objects.count(),
            'stocks': Stock.objects.count(),
        }

        self.assertEqual(initial_counts, rerun_counts)
        self.assertTrue(User.objects.filter(username='demo_admin', is_superuser=True).exists())
        self.assertTrue(User.objects.filter(username='demo_student').exists())

    def test_seed_demo_data_can_train_predictor(self):
        test_model_path = Path('ml/models_store/test_seed_predictor.pkl')
        test_model_path.unlink(missing_ok=True)

        call_command('seed_demo_data', '--train-predictor', '--model-output', str(test_model_path))

        self.assertTrue(test_model_path.exists())
        test_model_path.unlink(missing_ok=True)
