from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import Medicine


class Command(BaseCommand):
    help = "Create demo batches for the FEFO and expiry-risk demos (safe to run twice)."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        user = get_user_model().objects.filter(is_superuser=True).first()

        # (name, batch, stock, days until expiry, price)
        batches = [
            ("Amoxicillin 500mg", "B1", 20, 60, "15.50"),
            ("Amoxicillin 500mg", "B2", 50, 365, "15.50"),
            ("Paracetamol", "B-NEAR", 300, 15, "5.00"),
        ]

        for name, batch, stock, days, price in batches:
            _, created = Medicine.objects.get_or_create(
                name=name,
                batch_number=batch,
                defaults={
                    'stock_quantity': stock,
                    'expiry_date': today + timedelta(days=days),
                    'price': price,
                    'reorder_level': 10,
                    'added_by': user,
                },
            )
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f"{status}: {name} (batch {batch}), {stock} units, expires in {days} days")