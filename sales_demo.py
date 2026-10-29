import random
from datetime import timedelta
from django.utils import timezone
from inventory.models import Medicine, Sale

random.seed(7)
today = timezone.localdate()

# average units sold per day (Cetirizine is skipped: it is expired)
DAILY_AVG = {
    "Paracetamol 500mg": 12,   # fast seller
    "Amoxicillin 500mg": 3,
    "Ibuprofen 400mg": 4,
    "Coartem 20/120": 1,       # slow seller
    "ORS Sachet": 3,
    "Metformin 500mg": 4,
    "Vitamin C 500mg": 2,      # slow, and 300 in stock expiring soon
}

added = 0
for name, avg in DAILY_AVG.items():
    med = Medicine.objects.filter(name=name).order_by("expiry_date").first()
    if not med or Sale.objects.filter(medicine=med).exists():
        continue
    for d in range(60, 0, -1):
        qty = max(0, round(random.gauss(avg, avg * 0.4)))
        if qty:
            Sale.objects.create(
                medicine=med, medicine_name=med.name, quantity=qty,
                stock_after=med.stock_quantity,
                sale_date=today - timedelta(days=d),
            )
            added += 1

# Second batch of Amoxicillin (later expiry) so you can test oldest-first selling
Medicine.objects.get_or_create(
    name="Amoxicillin 500mg", batch_number="AMX-B2",
    defaults=dict(generic_name="Amoxicillin", category="Antibiotic", price=1200,
                  cost_price=800, stock_quantity=200, unit="capsule",
                  reorder_level=80, expiry_date=today + timedelta(days=300),
                  supplier="PharmaCare"),
)
print(f"Done. Added {added} sales.")
