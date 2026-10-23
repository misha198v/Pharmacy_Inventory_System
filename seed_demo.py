from datetime import timedelta
from django.utils import timezone
from inventory.models import Medicine

today = timezone.now().date()

# (name, generic, category, batch, price, cost, stock, unit, reorder, days_to_expiry, supplier)
MEDICINES = [
    ("Paracetamol 500mg", "Paracetamol", "Painkiller", "PCM-A1", 500, 300, 300, "tablet", 100, 120, "MediSupply Ltd"),
    ("Amoxicillin 500mg", "Amoxicillin", "Antibiotic", "AMX-A1", 1200, 800, 40, "capsule", 80, 20, "PharmaCare"),
    ("Ibuprofen 400mg", "Ibuprofen", "Painkiller", "IBU-A1", 700, 450, 25, "tablet", 60, 200, "MediSupply Ltd"),
    ("Coartem 20/120", "Artemether/Lumefantrine", "Antimalarial", "COA-A1", 6000, 4500, 60, "pack", 30, 90, "PharmaCare"),
    ("ORS Sachet", "Oral rehydration salts", "Rehydration", "ORS-A1", 800, 500, 120, "sachet", 50, 150, "HealthLine"),
    ("Cetirizine 10mg", "Cetirizine", "Antihistamine", "CET-A1", 600, 350, 30, "tablet", 40, -10, "HealthLine"),
    ("Metformin 500mg", "Metformin", "Diabetes", "MET-A1", 900, 600, 150, "tablet", 70, 180, "PharmaCare"),
    ("Vitamin C 500mg", "Ascorbic acid", "Supplement", "VTC-A1", 300, 150, 300, "tablet", 100, 25, "MediSupply Ltd"),
]

created = 0
for (name, generic, category, batch, price, cost, stock, unit, reorder, days, supplier) in MEDICINES:
    _, was_created = Medicine.objects.get_or_create(
        name=name,
        batch_number=batch,
        defaults=dict(
            generic_name=generic, category=category, price=price, cost_price=cost,
            stock_quantity=stock, unit=unit, reorder_level=reorder,
            expiry_date=today + timedelta(days=days), supplier=supplier,
        ),
    )
    created += int(was_created)

print(f"Done. Added {created} medicines. Total now: {Medicine.objects.count()}.")
