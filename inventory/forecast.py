"""Reorder suggestions from sales history.

How demand is measured
----------------------
Average daily demand = units sold per day over the last HISTORY_DAYS full days
(today is left out because it is not finished yet).

A day is NOT counted when the medicine could not have been sold on it: there
were no sales AND there was no sellable stock at the end of the day (it had not
been received yet, it was out of stock, or every batch had expired). Counting
those days as "zero demand" is what makes a forecast under-order right after a
stock-out, which then causes the next stock-out.

Stock on past days is rebuilt by walking backwards from today's stock, undoing
each sale and each stock addition recorded in InventoryLog (CREATE / UPDATE).
If stock was added in a way that is not logged (for example in the Django admin),
that day looks stocked, so it is counted as a normal day. That is the safe
direction: the forecast falls back to the plain average.
"""

import math
from collections import defaultdict
from datetime import timedelta
from statistics import mean, pstdev

from django.db.models import Sum
from django.utils import timezone

from .models import InventoryLog, Medicine, Sale

HISTORY_DAYS = 28        # how far back the baseline looks
Z = 1.65                 # safety factor: roughly "cover 95% of busy days"
MIN_RELIABLE_DAYS = 14   # fewer counted days than this -> flag low confidence


def _group_batches():
    """{lowercase medicine name: [its batches]}"""
    groups = defaultdict(list)
    for m in Medicine.objects.all():
        groups[m.name.lower()].append(m)
    return groups


def _closing_stock(batch, today, start, sold_on, added_on):
    """{day: units in this batch at the end of that day}, for start .. today-1.

    Starts from today's stock and undoes each day's sales and additions.
    """
    closing = {}
    stock = batch.stock_quantity
    day = today
    while day > start:
        stock += sold_on.get(day, 0) - added_on.get(day, 0)
        day -= timedelta(days=1)
        closing[day] = max(stock, 0)
    return closing


def demand_history(groups, today, days=HISTORY_DAYS):
    """{name: {'daily': [units sold on each counted day], 'stockout_days': n}}"""
    start = today - timedelta(days=days)

    # Demand: units sold per medicine name and day. Uses the name on the sale,
    # so sales from batches that were deleted later still count.
    sold_by_name = defaultdict(lambda: defaultdict(int))
    rows = (
        Sale.objects.filter(sale_date__gte=start, sale_date__lt=today)
        .values('medicine_name', 'sale_date')
        .annotate(total=Sum('quantity'))
    )
    for r in rows:
        sold_by_name[r['medicine_name'].lower()][r['sale_date']] += r['total']

    # Stock movements per batch, used to rebuild past stock levels.
    sold_by_batch = defaultdict(lambda: defaultdict(int))
    rows = (
        Sale.objects.filter(sale_date__gte=start, sale_date__lte=today, medicine__isnull=False)
        .values('medicine_id', 'sale_date')
        .annotate(total=Sum('quantity'))
    )
    for r in rows:
        sold_by_batch[r['medicine_id']][r['sale_date']] += r['total']

    added_by_batch = defaultdict(lambda: defaultdict(int))
    logs = InventoryLog.objects.filter(
        medicine__isnull=False,
        action__in=['CREATE', 'UPDATE'],
        timestamp__date__gte=start,
    ).values('medicine_id', 'stock_before', 'stock_after', 'timestamp')
    for log in logs:
        if log['stock_after'] is None:
            continue
        day = timezone.localtime(log['timestamp']).date()
        added_by_batch[log['medicine_id']][day] += log['stock_after'] - (log['stock_before'] or 0)

    history = {}
    for name, batches in groups.items():
        closings = [
            (b, _closing_stock(b, today, start, sold_by_batch[b.pk], added_by_batch[b.pk]))
            for b in batches
        ]
        sales_by_day = sold_by_name.get(name, {})
        daily, stockout_days = [], 0
        for i in range(days):
            day = start + timedelta(days=i)
            units = sales_by_day.get(day, 0)
            sellable = sum(c[day] for b, c in closings if day <= b.expiry_date)
            if units == 0 and sellable == 0:
                stockout_days += 1       # could not have sold anything: not "zero demand"
            else:
                daily.append(units)
        history[name] = {'daily': daily, 'stockout_days': stockout_days}
    return history


def units_at_risk(batches, daily, today):
    """Units expected to still be unsold when each batch expires (batches sorted soonest-expiry first)."""
    at_risk = 0.0
    stock_before = 0
    for b in batches:
        if b.expiry_date is not None:
            days_left = (b.expiry_date - today).days
            sold_from_b = min(max(daily * days_left - stock_before, 0), b.stock_quantity)
            at_risk += b.stock_quantity - sold_from_b
        stock_before += b.stock_quantity
    return int(round(at_risk))


def build_suggestions(lead_days=7, cover_days=14):
    today = timezone.localdate()
    groups = _group_batches()
    history = demand_history(groups, today)

    rank = {
        'ORDER_NOW': 0,
        'EXPIRY_RISK': 1,
        'ORDER_SOON': 2,
        'OK': 3,
        'OVERSTOCKED': 4,
        'NO_SALES_DATA': 5,
    }
    results = []

    for key, batches in groups.items():
        sellable = sorted(
            [b for b in batches if b.stock_quantity > 0 and b.expiry_date >= today],
            key=lambda b: (b.expiry_date, b.id),
        )
        on_hand = sum(b.stock_quantity for b in sellable)

        values = history[key]['daily']
        item = {
            'medicine_name': batches[0].name,
            'on_hand': on_hand,
            'days_of_data': len(values),
            'stockout_days_ignored': history[key]['stockout_days'],
        }

        if not values or sum(values) == 0:
            item.update(status='NO_SALES_DATA', avg_daily_demand=0, days_of_cover=None,
                        at_risk_units=0, suggested_order=None, low_confidence=None)
            results.append(item)
            continue

        avg, sd = mean(values), pstdev(values)
        at_risk = units_at_risk(sellable, avg, today)
        usable = on_hand - at_risk
        need = avg * (lead_days + cover_days) + Z * sd * math.sqrt(lead_days)
        suggested = max(0, math.ceil(need - usable))
        cover = on_hand / avg

        if cover < lead_days:
            status = 'ORDER_NOW'
        elif at_risk > 0:
            status = 'EXPIRY_RISK'
        elif suggested > 0:
            status = 'ORDER_SOON'
        elif cover > 90:
            status = 'OVERSTOCKED'
        else:
            status = 'OK'

        item.update(
            status=status,
            avg_daily_demand=round(avg, 2),
            days_of_cover=round(cover, 1),
            at_risk_units=at_risk,
            suggested_order=suggested,
            low_confidence=len(values) < MIN_RELIABLE_DAYS,
        )
        results.append(item)

    results.sort(key=lambda r: (rank[r['status']], r['days_of_cover'] if r['days_of_cover'] is not None else 9999))
    return results