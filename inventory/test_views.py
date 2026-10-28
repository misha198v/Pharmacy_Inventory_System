from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import InventoryLog, Medicine, UserProfile
from .views import (
    MedicineViewSet, dashboard_summary, expired_medicines,
    low_stock_medicines, medicine_history, near_expiry_medicines,
)

TODAY = timezone.localdate()


def batch(name, number, qty, days, reorder=10):
    return Medicine.objects.create(
        name=name, batch_number=number, price=2, stock_quantity=qty,
        reorder_level=reorder, expiry_date=TODAY + timedelta(days=days),
    )


class DashboardTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user('boss', password='x')
        UserProfile.objects.create(user=self.user, role='manager')

        batch('Amoxicillin', 'A1', 17, 10)        # old batch, expiring soon
        batch('Amoxicillin', 'A2', 200, 90)
        batch('Paracetamol', 'P1', 5, 200)        # genuinely low
        batch('Cetirizine', 'C1', 30, -5)         # expired, nothing sellable
        batch('Vitamin C', 'V1', 0, 15)           # empty batch, expiry close
        batch('Metformin', 'M1', 5, 60)           # nearly empty old batch ...
        batch('Metformin', 'M2', 200, 120)        # ... but a big newer batch behind it

    def get(self, view, **kwargs):
        request = self.factory.get('/x/')
        force_authenticate(request, user=self.user)
        return view(request, **kwargs)

    def test_dashboard_numbers(self):
        d = self.get(dashboard_summary).data
        self.assertEqual(d['total_medicines'], 5)     # distinct names
        self.assertEqual(d['total_batches'], 7)       # table rows
        # sellable units 17+200+5+0+5+200 = 427, at price 2
        self.assertEqual(float(d['total_stock_value']), 854.0)
        # the expired Cetirizine is reported separately, not in the stock value
        self.assertEqual(float(d['expired_stock_value']), 60.0)
        self.assertEqual(d['expired_units'], 30)
        # Paracetamol, Cetirizine (nothing sellable) and Vitamin C (empty) are low;
        # Metformin is NOT low just because its oldest batch has 5 left.
        self.assertEqual(d['low_stock_count'], 3)
        # only Amoxicillin A1; the empty Vitamin C batch is not counted
        self.assertEqual(d['expiring_soon_count'], 1)

    def test_low_stock_endpoint_matches_dashboard(self):
        rows = self.get(low_stock_medicines).data
        self.assertEqual({r['name'] for r in rows}, {'Paracetamol', 'Cetirizine', 'Vitamin C'})

    def test_expired_lists_only_batches_with_units(self):
        batch('Ibuprofen', 'I1', 0, -9)           # expired but empty: nothing to remove
        rows = self.get(expired_medicines).data
        self.assertEqual([r['batch_number'] for r in rows], ['C1'])

    def test_near_expiry_lists_in_date_batches_with_stock(self):
        rows = self.get(near_expiry_medicines).data
        self.assertEqual([r['batch_number'] for r in rows], ['A1'])

    def test_near_expiry_boundary_matches_model_status(self):
        edge_in = batch('Edge', 'E29', 5, 29)
        edge_out = batch('Edge', 'E30', 5, 30)
        self.assertEqual(edge_in.status, 'EXPIRING')
        self.assertNotEqual(edge_out.status, 'EXPIRING')
        numbers = [r['batch_number'] for r in self.get(near_expiry_medicines).data]
        self.assertIn('E29', numbers)
        self.assertNotIn('E30', numbers)

    def test_name_case_is_ignored_when_grouping(self):
        batch('amoxicillin', 'A3', 10, 100)
        d = self.get(dashboard_summary).data
        self.assertEqual(d['total_medicines'], 5)

    def test_history_endpoint_and_viewset_action_agree(self):
        med = Medicine.objects.get(batch_number='A1')
        InventoryLog.objects.create(medicine=med, medicine_name=med.name, action='UPDATE',
                                    stock_before=1, stock_after=2, performed_by=self.user)
        a = self.get(medicine_history, medicine_id=med.pk).data
        request = self.factory.get('/x/')
        force_authenticate(request, user=self.user)
        b = MedicineViewSet.as_view({'get': 'history'})(request, pk=med.pk).data
        self.assertEqual(len(a), 1)
        self.assertEqual(a, b)