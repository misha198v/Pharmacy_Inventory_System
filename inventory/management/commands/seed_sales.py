import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import Medicine, Sale


class Command(BaseCommand):
    help = "Generate SIMULATED daily sales for demo and forecast testing (sold_by is left empty)."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=120)
        parser.add_argument('--clear', action='store_true', help='Remove simulated sales')

    def handle(self, *args, **opts):
        if opts['clear']:
            deleted, _ = Sale.objects.filter(sold_by__isnull=True).delete()
            self.stdout.write(f'Removed {deleted} simulated sales.')
            return

        rng = random.Random(42)  # same seed = same data every run
        today = timezone.localdate()
        days = opts['days']

        # one entry per medicine name (the newest batch stands in for the product)
        products = {}
        for m in Medicine.objects.order_by('-id'):
            products.setdefault(m.name.lower(), m)

        weekday_factor = [1.1, 1.0, 1.0, 1.0, 1.2, 1.3, 0.6]  # Mon..Sun
        rows = []
        for med in products.values():
            base = rng.uniform(1, 12)           # typical units per day
            trend = rng.uniform(-0.002, 0.004)  # slowly rising or falling demand
            for i in range(days, 0, -1):
                day = today - timedelta(days=i)
                expected = base * (1 + trend * (days - i)) * weekday_factor[day.weekday()]
                qty = max(0, round(rng.gauss(expected, expected ** 0.5 + 0.5)))
                if qty:
                    rows.append(Sale(
                        medicine=med, medicine_name=med.name, quantity=qty,
                        stock_after=999,  # placeholder: simulated rows never count as stock-outs
                        sale_date=day, sold_by=None,
                    ))

        Sale.objects.bulk_create(rows)
        self.stdout.write(f'Created {len(rows)} simulated sales for {len(products)} medicines.')