from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import InventoryLog, Medicine, Sale, UserProfile
from .sales_views import sales

TODAY = timezone.localdate()


def batch(name, number, qty, days):
    return Medicine.objects.create(
        name=name, batch_number=number, price=1,
        stock_quantity=qty, expiry_date=TODAY + timedelta(days=days),
    )


class SaleFefoTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.staff = User.objects.create_user('staff1', password='x')
        UserProfile.objects.create(user=self.staff, role='staff')
        self.manager = User.objects.create_user('boss', password='x')
        UserProfile.objects.create(user=self.manager, role='manager')

    def post(self, user, data):
        request = self.factory.post('/sales/', data, format='json')
        force_authenticate(request, user=user)
        return sales(request)

    def stock(self, number):
        return Medicine.objects.get(batch_number=number).stock_quantity

    def test_sale_spans_batches_oldest_first(self):
        batch('Amox', 'NEW', 50, 90)
        batch('Amox', 'OLD', 17, 20)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 20})
        self.assertEqual(r.status_code, 201)
        self.assertEqual([(a['batch_number'], a['quantity']) for a in r.data['allocations']],
                         [('OLD', 17), ('NEW', 3)])
        self.assertEqual(self.stock('OLD'), 0)
        self.assertEqual(self.stock('NEW'), 47)
        self.assertEqual(Sale.objects.count(), 2)
        self.assertEqual(InventoryLog.objects.filter(action='SALE').count(), 2)

    def test_newer_batch_untouched_while_older_has_stock(self):
        batch('Amox', 'NEW', 50, 90)
        batch('Amox', 'OLD', 17, 20)
        self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 5})
        self.assertEqual(self.stock('OLD'), 12)
        self.assertEqual(self.stock('NEW'), 50)

    def test_expired_batch_is_never_sold(self):
        batch('Amox', 'DEAD', 100, -3)
        batch('Amox', 'OK', 5, 40)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 10})
        self.assertEqual(r.status_code, 400)
        self.assertIn('Only 5', r.data['detail'])
        self.assertEqual(self.stock('DEAD'), 100)

    def test_only_expired_stock_explains_why(self):
        batch('Amox', 'DEAD', 30, -1)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 1})
        self.assertEqual(r.status_code, 400)
        self.assertIn('30 expired', r.data['detail'])

    def test_unknown_medicine(self):
        r = self.post(self.staff, {'medicine_name': 'Nothing', 'quantity': 1})
        self.assertEqual(r.status_code, 400)
        self.assertIn('not found', r.data['detail'])

    def test_not_enough_stock_changes_nothing(self):
        batch('Amox', 'A', 5, 20)
        batch('Amox', 'B', 5, 40)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 11})
        self.assertEqual(r.status_code, 400)
        self.assertEqual((self.stock('A'), self.stock('B')), (5, 5))
        self.assertEqual(Sale.objects.count(), 0)

    def test_name_is_case_insensitive(self):
        batch('Amoxicillin 500mg', 'A', 10, 20)
        r = self.post(self.staff, {'medicine_name': ' amoxicillin 500MG ', 'quantity': 4})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.stock('A'), 6)

    def test_same_expiry_is_stable_by_id(self):
        first = batch('Amox', 'FIRST', 5, 30)
        batch('Amox', 'SECOND', 5, 30)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 3})
        self.assertEqual(r.data['allocations'][0]['batch_id'], first.pk)

    def test_bad_quantity(self):
        batch('Amox', 'A', 5, 20)
        for q in (0, -2, 'abc', None):
            r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': q})
            self.assertEqual(r.status_code, 400, q)

    def test_dry_run_changes_nothing(self):
        batch('Amox', 'OLD', 17, 20)
        batch('Amox', 'NEW', 50, 90)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 20, 'dry_run': True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([(a['batch_number'], a['quantity']) for a in r.data['allocations']],
                         [('OLD', 17), ('NEW', 3)])
        self.assertEqual((self.stock('OLD'), self.stock('NEW')), (17, 50))
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(InventoryLog.objects.count(), 0)

    # ---- manager override ----
    def test_staff_cannot_override(self):
        batch('Amox', 'OLD', 17, 20)
        new = batch('Amox', 'NEW', 50, 90)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 5,
                                   'override_batch_id': new.pk, 'reason': 'damaged'})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.stock('OLD'), 17)

    def test_override_needs_a_reason(self):
        batch('Amox', 'OLD', 17, 20)
        new = batch('Amox', 'NEW', 50, 90)
        r = self.post(self.manager, {'medicine_name': 'Amox', 'quantity': 5,
                                     'override_batch_id': new.pk})
        self.assertEqual(r.status_code, 400)

    def test_manager_override_sells_chosen_batch_first_and_logs_reason(self):
        batch('Amox', 'OLD', 17, 20)
        new = batch('Amox', 'NEW', 50, 90)
        r = self.post(self.manager, {'medicine_name': 'Amox', 'quantity': 5,
                                     'override_batch_id': new.pk,
                                     'reason': 'Old batch box crushed'})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data['override'])
        self.assertEqual((self.stock('OLD'), self.stock('NEW')), (17, 45))
        log = InventoryLog.objects.get(action='SALE')
        self.assertIn('Old batch box crushed', log.reason)

    def test_override_of_expired_or_other_medicine_is_refused(self):
        batch('Amox', 'OK', 10, 20)
        dead = batch('Amox', 'DEAD', 10, -2)
        other = batch('Para', 'P1', 10, 50)
        for bad in (dead, other):
            r = self.post(self.manager, {'medicine_name': 'Amox', 'quantity': 1,
                                         'override_batch_id': bad.pk, 'reason': 'x'})
            self.assertEqual(r.status_code, 400)

    def test_choosing_the_already_first_batch_is_not_an_override(self):
        old = batch('Amox', 'OLD', 17, 20)
        batch('Amox', 'NEW', 50, 90)
        r = self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 1})
        self.assertFalse(r.data['override'])
        r = self.post(self.manager, {'medicine_name': 'Amox', 'quantity': 1,
                                     'override_batch_id': old.pk, 'reason': 'x'})
        self.assertFalse(r.data['override'])
        self.assertEqual(InventoryLog.objects.filter(reason__startswith='FEFO').count(), 0)

    def test_get_lists_recent_sales_with_batch_number(self):
        batch('Amox', 'A', 10, 20)
        self.post(self.staff, {'medicine_name': 'Amox', 'quantity': 2})
        request = self.factory.get('/sales/')
        force_authenticate(request, user=self.staff)
        r = sales(request)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data[0]['batch_number'], 'A')
        self.assertEqual(r.data[0]['sold_by'], 'staff1')