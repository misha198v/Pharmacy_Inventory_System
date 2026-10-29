from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import InventoryLog, Medicine, UserProfile
from .sales_views import sales
from .scan_views import link_barcode, scan

TODAY = timezone.localdate()


def batch(name, number, qty, days, barcode=None):
    return Medicine.objects.create(
        name=name, batch_number=number, price=1, stock_quantity=qty,
        expiry_date=TODAY + timedelta(days=days), barcode=barcode,
    )


class ScanTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.staff = User.objects.create_user('staff1', password='x')
        UserProfile.objects.create(user=self.staff, role='staff')
        self.manager = User.objects.create_user('boss', password='x')
        UserProfile.objects.create(user=self.manager, role='manager')

        self.a = batch('Amoxicillin 500mg', 'A', 17, 20, '6001')    # oldest, sell first
        self.b = batch('Amoxicillin 500mg', 'B', 200, 90, '6001')
        batch('Paracetamol 500mg', 'P1', 30, 200, '6002')           # only one batch

    def call(self, view, data, user=None):
        request = self.factory.post('/x/', data, format='json')
        force_authenticate(request, user=user or self.staff)
        return view(request)

    def scan(self, **data):
        r = self.call(scan, data)
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    # ---- identifying the medicine ----
    def test_unknown_barcode(self):
        v = self.scan(code='9999')
        self.assertEqual(v['status'], 'UNKNOWN_CODE')
        self.assertFalse(v['ok'])
        self.assertEqual(v['code'], '9999')

    def test_nothing_to_scan_is_refused(self):
        self.assertEqual(self.call(scan, {}).status_code, 400)

    def test_single_batch_medicine_needs_only_the_barcode(self):
        v = self.scan(code='6002')
        self.assertTrue(v['ok'])
        self.assertEqual(v['status'], 'OK')
        self.assertEqual(v['expected_batch']['batch_number'], 'P1')

    def test_typed_name_works_when_a_pack_cannot_be_scanned(self):
        v = self.scan(medicine_name='  paracetamol 500MG ')
        self.assertEqual(v['status'], 'OK')

    def test_unknown_typed_name(self):
        self.assertEqual(self.scan(medicine_name='Nothing')['status'], 'UNKNOWN_MEDICINE')

    # ---- FEFO: the batch on the pack ----
    def test_several_batches_ask_for_the_batch_number(self):
        v = self.scan(code='6001')
        self.assertFalse(v['ok'])
        self.assertEqual(v['status'], 'CONFIRM_BATCH')
        self.assertEqual(v['expected_batch']['batch_number'], 'A')
        self.assertEqual([(q['batch_number'], q['state']) for q in v['queue']],
                         [('A', 'next'), ('B', 'locked')])
        self.assertIn('batch A', v['message'])

    def test_right_batch_is_accepted_ignoring_case_and_spaces(self):
        for typed in ('A', ' a ', 'a'):
            v = self.scan(code='6001', batch_number=typed)
            self.assertEqual(v['status'], 'OK', typed)

    def test_newer_batch_is_blocked_while_older_has_stock(self):
        v = self.scan(code='6001', batch_number='B')
        self.assertFalse(v['ok'])
        self.assertEqual(v['status'], 'BLOCKED')
        self.assertIn('This pack is batch B.', v['message'])
        self.assertIn('Batch A (17 left, expires', v['message'])   # keeps the batch name's case
        self.assertIn('take batch A', v['message'])

    def test_batch_names_keep_their_case_in_messages(self):
        batch('Zinc 20mg', 'zn-9a', 5, 10, '6006')
        batch('Zinc 20mg', 'ZN-10B', 5, 80, '6006')
        v = self.scan(code='6006', batch_number='ZN-10B')
        self.assertIn('Batch zn-9a (5 left', v['message'])
        self.assertIn('take batch zn-9a', v['message'])

    def test_dates_are_written_the_same_way_everywhere(self):
        v = self.scan(code='6001')
        self.assertEqual(v['queue'][0]['expiry_pretty'], f"{self.a.expiry_date.day} "
                         f"{self.a.expiry_date.strftime('%b')} {self.a.expiry_date.year}")
        self.assertIn(v['queue'][0]['expiry_pretty'], v['message'])

    def test_expired_pack_is_refused(self):
        batch('Amoxicillin 500mg', 'X', 8, -3, '6001')
        v = self.scan(code='6001', batch_number='X')
        self.assertEqual(v['status'], 'EXPIRED')
        self.assertFalse(v['ok'])

    def test_batch_not_recorded(self):
        self.assertEqual(self.scan(code='6001', batch_number='ZZZ')['status'], 'UNKNOWN_BATCH')

    def test_empty_batch_is_refused(self):
        batch('Amoxicillin 500mg', 'EMPTY', 0, 50, '6001')
        self.assertEqual(self.scan(code='6001', batch_number='EMPTY')['status'], 'BATCH_EMPTY')

    # ---- counting what is already in the sale ----
    def test_units_already_in_the_sale_move_the_next_pack_to_the_next_batch(self):
        basket = {'amoxicillin 500mg': 17}                   # all of batch A is counted
        used = self.scan(code='6001', batch_number='A', basket=basket)
        self.assertEqual(used['status'], 'BATCH_USED_UP')
        ok = self.scan(code='6001', batch_number='B', basket=basket)
        self.assertEqual(ok['status'], 'OK')
        self.assertEqual([q['state'] for q in ok['queue']], ['used', 'next'])

    def test_partly_counted_batch_still_expected(self):
        v = self.scan(code='6001', batch_number='A', basket={'amoxicillin 500mg': 16})
        self.assertEqual(v['status'], 'OK')
        self.assertEqual(v['expected_batch']['units_left'], 1)

    def test_everything_already_in_the_sale(self):
        v = self.scan(code='6001', basket={'amoxicillin 500mg': 217})
        self.assertEqual(v['status'], 'OUT_OF_STOCK')

    def test_bad_basket_is_ignored(self):
        for bad in ('x', [1], {'amoxicillin 500mg': 'abc'}, {'amoxicillin 500mg': -5}):
            self.assertEqual(self.scan(code='6002', basket=bad)['status'], 'OK', bad)

    # ---- stock states ----
    def test_only_expired_stock(self):
        batch('Cetirizine 10mg', 'C1', 30, -5, '6003')
        v = self.scan(code='6003')
        self.assertEqual(v['status'], 'EXPIRED')
        self.assertIn('30 units', v['message'])

    def test_out_of_stock(self):
        batch('Zinc', 'Z1', 0, 100, '6004')
        self.assertEqual(self.scan(code='6004')['status'], 'OUT_OF_STOCK')

    def test_expired_stock_on_the_shelf_means_the_pack_must_be_confirmed(self):
        # One in-date batch, but expired units are still on the shelf: the pack in
        # hand could be the expired one, so the batch number is needed.
        batch('Cetirizine 10mg', 'C1', 30, -5, '6003')
        batch('Cetirizine 10mg', 'C2', 10, 60, '6003')
        self.assertEqual(self.scan(code='6003')['status'], 'CONFIRM_BATCH')
        self.assertEqual(self.scan(code='6003', batch_number='C1')['status'], 'EXPIRED')
        self.assertEqual(self.scan(code='6003', batch_number='C2')['status'], 'OK')

    def test_no_batch_number_recorded_means_no_confirmation_possible(self):
        batch('Loose', None, 10, 30, '6005')
        batch('Loose', None, 10, 60, '6005')
        self.assertEqual(self.scan(code='6005')['status'], 'OK')

    # ---- the scan screen and the sale agree ----
    def test_scanned_packs_and_the_saved_sale_use_the_same_batches(self):
        basket, used = {}, []
        for _ in range(20):
            first = self.scan(code='6001', basket=basket)
            expected = first['expected_batch']['batch_number']
            v = self.scan(code='6001', batch_number=expected, basket=basket)
            self.assertEqual(v['status'], 'OK')
            used.append(expected)
            basket['amoxicillin 500mg'] = basket.get('amoxicillin 500mg', 0) + 1
        self.assertEqual((used.count('A'), used.count('B')), (17, 3))

        r = self.call(sales, {'medicine_name': 'Amoxicillin 500mg', 'quantity': 20})
        self.assertEqual(r.status_code, 201)
        self.assertEqual([(a['batch_number'], a['quantity']) for a in r.data['allocations']],
                         [('A', 17), ('B', 3)])


class LinkBarcodeTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.staff = User.objects.create_user('staff1', password='x')
        UserProfile.objects.create(user=self.staff, role='staff')
        self.manager = User.objects.create_user('boss', password='x')
        UserProfile.objects.create(user=self.manager, role='manager')
        batch('Ibuprofen 400mg', 'I1', 10, 100)
        batch('Ibuprofen 400mg', 'I2', 10, 200)
        batch('Paracetamol 500mg', 'P1', 30, 200, '6002')

    def link(self, user, **data):
        request = self.factory.post('/x/', data, format='json')
        force_authenticate(request, user=user)
        return link_barcode(request)

    def test_staff_cannot_link(self):
        r = self.link(self.staff, code='7001', medicine_name='Ibuprofen 400mg')
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Medicine.objects.filter(barcode='7001').exists())

    def test_manager_links_every_batch_and_it_is_logged(self):
        r = self.link(self.manager, code='7001', medicine_name='ibuprofen 400MG')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['batches'], 2)
        self.assertEqual(Medicine.objects.filter(barcode='7001').count(), 2)
        self.assertEqual(InventoryLog.objects.filter(reason='Barcode linked: 7001').count(), 2)

    def test_scan_works_after_linking(self):
        self.link(self.manager, code='7001', medicine_name='Ibuprofen 400mg')
        request = APIRequestFactory().post('/x/', {'code': '7001'}, format='json')
        force_authenticate(request, user=self.staff)
        v = scan(request).data
        self.assertEqual(v['status'], 'CONFIRM_BATCH')       # two batches, so confirm the pack
        self.assertEqual(v['medicine'], 'Ibuprofen 400mg')

    def test_barcode_cannot_belong_to_two_medicines(self):
        r = self.link(self.manager, code='6002', medicine_name='Ibuprofen 400mg')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Paracetamol', r.data['detail'])

    def test_unknown_medicine_and_missing_fields(self):
        self.assertEqual(self.link(self.manager, code='7001', medicine_name='Nope').status_code, 400)
        self.assertEqual(self.link(self.manager, code='', medicine_name='Ibuprofen 400mg').status_code, 400)
        self.assertEqual(self.link(self.manager, code='x' * 65, medicine_name='Ibuprofen 400mg').status_code, 400)

    def test_linking_again_is_harmless(self):
        self.link(self.manager, code='7001', medicine_name='Ibuprofen 400mg')
        r = self.link(self.manager, code='7001', medicine_name='Ibuprofen 400mg')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(InventoryLog.objects.filter(reason='Barcode linked: 7001').count(), 2)