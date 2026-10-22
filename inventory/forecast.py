import math
from collections import defaultdict
from datetime import timedelta
from statistics import mean, pstdev

from django.db.models import Sum
from django.utils import timezone

from .models import Medicine, Sale

HISTORY_DAYS = 28   # how far back the baseline looks
Z = 1.65            # safety factor: roughly "cover 95% of busy days"


def daily_series(days=HISTORY_DAYS):
    """{medicine name (lowercase): [units sold on each of the last `days` days]}"""
    today = timezone.localdate()
    start = today - timedelta(days=days)
    rows = (
        Sale.objects.filter(sale_date__gte=start, sale_date__lt=today)
        .values('medicine_name', 'sale_date')
        .annotate(total=Sum('quantity'))
    )
    per_name = defaultdict(dict)
    for r in rows:
        per_name[r['medicine_name'].lower()][r['sale_date']] = r['total']
    return {
        name: [by_date.get(start + timedelta(i), 0) for i in range(days)]
        for name, by_date in per_name.items()
    }


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
    series = daily_series()

    groups = defaultdict(list)
    for m in Medicine.objects.all():
        groups[m.name.lower()].append(m)

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
            [b for b in batches
             if b.stock_quantity > 0 and (b.expiry_date is None or b.expiry_date >= today)],
            key=lambda b: (b.expiry_date is None, b.expiry_date or today),
        )
        on_hand = sum(b.stock_quantity for b in sellable)
        item = {'medicine_name': batches[0].name, 'on_hand': on_hand}

        values = series.get(key)
        if not values or sum(values) == 0:
            item.update(status='NO_SALES_DATA', avg_daily_demand=0, days_of_cover=None,
                        at_risk_units=0, suggested_order=None)
            results.append(item)
            continue

        avg, sd = mean(values), pstdev(values)
        at_risk = units_at_risk(sellable, avg, today)
        usable = on_hand - at_risk
        need = avg * (lead_days + cover_days) + Z * sd * math.sqrt(lead_days)
        suggested = max(0, math.ceil(need - usable))
        cover = on_hand / avg if avg > 0 else None

        if cover is not None and cover < lead_days:
            status = 'ORDER_NOW'
        elif at_risk > 0:
            status = 'EXPIRY_RISK'
        elif suggested > 0:
            status = 'ORDER_SOON'
        elif cover is not None and cover > 90:
            status = 'OVERSTOCKED'
        else:
            status = 'OK'

        item.update(
            status=status,
            avg_daily_demand=round(avg, 2),
            days_of_cover=round(cover, 1) if cover is not None else None,
            at_risk_units=at_risk,
            suggested_order=suggested,
        )
        results.append(item)

    results.sort(key=lambda r: (rank[r['status']], r['days_of_cover'] if r['days_of_cover'] is not None else 9999))
    return results