import math
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .forecast import build_suggestions
from .forecast_views import reorder_suggestions
from .models import InventoryLog, Medicine, Sale

TODAY = timezone.localdate()


def batch(name, number, qty, days_to_expiry=365):
    return Medicine.objects.create(
        name=name, batch_number=number, price=1, stock_quantity=qty,
        expiry_date=TODAY + timedelta(days=days_to_expiry),
    )


def sell(b, days_ago, qty, name=None):
    Sale.objects.create(
        medicine=b, medicine_name=name or b.name, quantity=qty,
        stock_after=0, sale_date=TODAY - timedelta(days=days_ago),
    )


def sell_every_day(b, qty):
    for ago in range(28, 0, -1):          # the 28 full days before today
        sell(b, ago, qty)


def log(b, action, before, after, days_ago):
    entry = InventoryLog.objects.create(
        medicine=b, medicine_name=b.name, action=action,
        stock_before=before, stock_after=after,
    )
    InventoryLog.objects.filter(pk=entry.pk).update(
        timestamp=timezone.now() - timedelta(days=days_ago)
    )


def suggestion(name):
    return next(s for s in build_suggestions() if s['medicine_name'] == name)


class DemandTests(TestCase):
    def test_steady_demand(self):
        b = batch('Para', 'P1', 100)
        sell_every_day(b, 5)
        s = suggestion('Para')
        self.assertEqual(s['avg_daily_demand'], 5.0)
        self.assertEqual(s['days_of_cover'], 20.0)
        self.assertEqual(s['days_of_data'], 28)
        self.assertEqual(s['stockout_days_ignored'], 0)
        self.assertFalse(s['low_confidence'])
        # need = 5 * (7 + 14) = 105, usable 100 -> order 5
        self.assertEqual(s['suggested_order'], 5)
        self.assertEqual(s['status'], 'ORDER_SOON')

    def test_stockout_days_are_not_counted_as_zero_demand(self):
        # Sold 10/day for 14 days, empty for 13 days, restocked 50 yesterday.
        b = batch('Para', 'P1', 50)
        for ago in range(28, 14, -1):
            sell(b, ago, 10)
        log(b, 'UPDATE', 0, 50, days_ago=1)
        s = suggestion('Para')
        self.assertEqual(s['stockout_days_ignored'], 13)
        self.assertEqual(s['days_of_data'], 15)
        self.assertAlmostEqual(s['avg_daily_demand'], 140 / 15, places=2)   # 9.33, not 5.0

    def test_unlogged_restock_falls_back_to_plain_average(self):
        # Same sales, but nothing recorded the restock: nothing is excluded.
        b = batch('Para', 'P1', 50)
        for ago in range(28, 14, -1):
            sell(b, ago, 10)
        s = suggestion('Para')
        self.assertEqual(s['stockout_days_ignored'], 0)
        self.assertEqual(s['avg_daily_demand'], 5.0)

    def test_new_medicine_is_not_diluted_by_days_before_it_existed(self):
        b = batch('New', 'N1', 80)
        log(b, 'CREATE', None, 100, days_ago=5)
        for ago in range(5, 0, -1):
            sell(b, ago, 4)
        s = suggestion('New')
        self.assertEqual(s['avg_daily_demand'], 4.0)       # 20 units / 5 days, not 20 / 28
        self.assertEqual(s['days_of_data'], 5)
        self.assertEqual(s['stockout_days_ignored'], 23)
        self.assertTrue(s['low_confidence'])

    def test_days_after_every_batch_expired_are_not_counted(self):
        b = batch('Old', 'O1', 0, days_to_expiry=-10)
        for ago in range(28, 10, -1):
            sell(b, ago, 5)
        s = suggestion('Old')
        self.assertEqual(s['avg_daily_demand'], 5.0)
        self.assertEqual(s['stockout_days_ignored'], 10)
        self.assertEqual(s['status'], 'ORDER_NOW')          # nothing sellable left

    def test_sales_names_that_differ_only_in_case_are_added_together(self):
        b = batch('Amox', 'A1', 100)
        sell(b, 3, 3, name='Amox')
        sell(b, 3, 4, name='amox')
        self.assertEqual(suggestion('Amox')['avg_daily_demand'], round(7 / 28, 2))

    def test_no_sales_in_window(self):
        batch('Quiet', 'Q1', 20)
        s = suggestion('Quiet')
        self.assertEqual(s['status'], 'NO_SALES_DATA')
        self.assertIsNone(s['suggested_order'])


class StatusTests(TestCase):
    def test_order_now_when_cover_is_shorter_than_lead_time(self):
        b = batch('Para', 'P1', 10)
        sell_every_day(b, 5)
        s = suggestion('Para')
        self.assertEqual(s['status'], 'ORDER_NOW')           # 2 days of cover, 7 day lead time
        self.assertEqual(s['suggested_order'], 95)           # 105 needed - 10 on hand

    def test_ok(self):
        b = batch('Para', 'P1', 120)
        sell_every_day(b, 5)
        s = suggestion('Para')
        self.assertEqual((s['status'], s['suggested_order']), ('OK', 0))

    def test_overstocked(self):
        b = batch('Para', 'P1', 500)
        sell_every_day(b, 5)
        self.assertEqual(suggestion('Para')['status'], 'OVERSTOCKED')

    def test_expiry_risk_counts_units_that_will_expire_unsold(self):
        soon = batch('Vit', 'V1', 20, days_to_expiry=10)
        later = batch('Vit', 'V2', 100, days_to_expiry=365)
        sell_every_day(soon, 1)                              # 1 unit a day
        s = suggestion('Vit')
        # In 10 days only 10 of the 20 units sell, so 10 will expire unsold.
        self.assertEqual(s['at_risk_units'], 10)
        self.assertEqual(s['status'], 'EXPIRY_RISK')
        self.assertEqual(s['suggested_order'], 0)

    def test_safety_stock_for_uneven_demand(self):
        b = batch('Para', 'P1', 100)
        for ago in range(28, 0, -1):
            sell(b, ago, 10 if ago % 2 == 0 else 0)          # mean 5, std dev 5
        s = suggestion('Para')
        self.assertEqual(s['avg_daily_demand'], 5.0)
        expected = math.ceil(5 * 21 + 1.65 * 5 * math.sqrt(7) - 100)
        self.assertEqual(s['suggested_order'], expected)     # 27

    def test_results_are_sorted_most_urgent_first(self):
        a = batch('A-ok', 'A1', 120)
        sell_every_day(a, 5)
        b = batch('B-urgent', 'B1', 10)
        sell_every_day(b, 5)
        batch('C-quiet', 'C1', 20)
        names = [s['medicine_name'] for s in build_suggestions()]
        self.assertEqual(names, ['B-urgent', 'A-ok', 'C-quiet'])


class ForecastViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user('staff1', password='x')

    def get(self, query=''):
        request = self.factory.get('/reorder/' + query)
        force_authenticate(request, user=self.user)
        return reorder_suggestions(request)

    def test_default_ok(self):
        batch('Para', 'P1', 10)
        self.assertEqual(self.get().status_code, 200)

    def test_bad_values_refused(self):
        for q in ('?lead_days=abc', '?lead_days=0', '?cover_days=-3',
                  '?lead_days=9999', '?cover_days=1.5'):
            self.assertEqual(self.get(q).status_code, 400, q)

    def test_longer_lead_time_orders_more(self):
        b = batch('Para', 'P1', 100)
        sell_every_day(b, 5)
        short = self.get('?lead_days=3').data[0]['suggested_order']
        long_ = self.get('?lead_days=14').data[0]['suggested_order']
        self.assertGreater(long_, short)