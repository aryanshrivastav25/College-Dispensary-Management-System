
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from inventory.models import Medicine, Stock

User = get_user_model()


class InventoryFlowTests(TestCase):
    """Regression tests for inventory CRUD and alert views."""

    def setUp(self):
        self.pharmacist_user = User.objects.create_user(username='inventory-pharmacist', password='safe-pass-123')
        self.student_user = User.objects.create_user(username='inventory-student', password='safe-pass-123')
        self.pharmacist_user.profile.role = UserProfile.Role.PHARMACIST
        self.pharmacist_user.profile.save(update_fields=['role'])
        self.stock = Stock.objects.create(
            medicine=Medicine.objects.create(
                name='Paracetamol',
                category=Medicine.Category.ANALGESIC,
                unit=Medicine.Unit.TABLET,
                description='Pain relief tablets',
            ),
            quantity=4,
            season_tag=Stock.SeasonTag.GENERAL,
        )
        self.normal_stock = Stock.objects.create(
            medicine=Medicine.objects.create(
                name='Vitamin C',
                category=Medicine.Category.SUPPLEMENT,
                unit=Medicine.Unit.BOTTLE,
                description='Daily supplement',
            ),
            quantity=18,
            season_tag=Stock.SeasonTag.WINTER,
        )

    def test_pharmacist_can_create_inventory_entry(self):
        self.client.force_login(self.pharmacist_user)

        response = self.client.post(
            reverse('inventory:add'),
            data={
                'medicine-name': 'Bandage Roll',
                'medicine-category': Medicine.Category.FIRST_AID,
                'medicine-unit': Medicine.Unit.BOX,
                'medicine-description': 'Sterile dressing rolls',
                'stock-quantity': '12',
                'stock-season_tag': Stock.SeasonTag.GENERAL,
            },
        )

        self.assertRedirects(response, reverse('inventory:list'))
        self.assertTrue(Stock.objects.filter(medicine__name='Bandage Roll', quantity=12).exists())

    def test_pharmacist_can_edit_inventory_entry(self):
        self.client.force_login(self.pharmacist_user)

        response = self.client.post(
            reverse('inventory:edit', kwargs={'pk': self.stock.pk}),
            data={
                'medicine-name': 'Paracetamol',
                'medicine-category': Medicine.Category.ANALGESIC,
                'medicine-unit': Medicine.Unit.TABLET,
                'medicine-description': 'Updated pain relief tablets',
                'stock-quantity': '9',
                'stock-season_tag': Stock.SeasonTag.MONSOON,
            },
        )

        self.assertRedirects(response, reverse('inventory:list'))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 9)
        self.assertEqual(self.stock.season_tag, Stock.SeasonTag.MONSOON)

    def test_alerts_view_only_shows_low_stock_items(self):
        self.client.force_login(self.pharmacist_user)

        response = self.client.get(reverse('inventory:alerts'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paracetamol')
        self.assertNotContains(response, 'Vitamin C')

    def test_student_cannot_access_inventory_list(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse('inventory:list'))

        self.assertEqual(response.status_code, 403)
