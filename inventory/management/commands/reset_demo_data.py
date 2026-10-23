import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from inventory.audit import log_change
from inventory.models import InventoryLog, Medicine, PurchaseOrder, Sale, UserProfile

MANAGER = ('manager1', 'manager123')
STAFF = ('staff1', 'staff123')

# (name, batch, stock, days until expiry, price, reorder level, average sales per day)
DEMO = [
    ('Paracetamol', 'P1', 100, 600, '5.00', 10, 7),
    ('Paracetamol', 'B-NEAR', 300, 15, '5.00', 10, 0),       # a big batch that expires soon
    ('Amoxil 500mg', 'A1', 120, 700, '15.50', 10, 8.3),
    ('Lipitor 20mg', 'L1', 85, 500, '34.60', 10, 4.6),
    ('Glucophage 850mg', 'G1', 200, 800, '12.00', 10, 4.2),
    ('Amoxicillin 500mg', 'B1', 20, 60, '15.50', 10, 6),       # two batches: FEFO demo
    ('Amoxicillin 500mg', 'B2', 50, 365, '15.50', 10, 0),
    ('Ibuprofen 400mg', 'I1', 8, 400, '6.00', 10, 3),          # already below its reorder level
    ('Cetirizine 10mg', 'C1', 60, 20, '4.50', 10, 3),          # expires within a month
    ('Old Syrup', 'OLD1', 40, -10, '8.00', 10, 0),             # expired, still has stock: write-off demo
]


class Command(BaseCommand):
    help = (
        "Wipe medicines, sales, orders and history, then load demo data. "
        "By default it also creates two demo logins (manager1 and staff1). "
        "Add --no-demo-users to create no accounts and use the manager you already have."
    )

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Confirm that you want to wipe the data')
        parser.add_argument('--days', type=int, default=120, help='Days of simulated sales')
        parser.add_argument(
            '--no-demo-users', action='store_true',
            help='Do not create manager1 / staff1. Create your users in the app instead.',
        )

    def handle(self, *args, **opts):
        if not opts['yes']:
            self.stdout.write(
                "This deletes ALL medicines, sales, purchase orders and history, then loads demo data.\n"
                "Run again with --yes to go ahead:  python manage.py reset_demo_data --yes"
            )
            return

        User = get_user_model()
        today = timezone.localdate()

        # Who the demo batches are recorded under. Decided BEFORE anything is deleted.
        existing_owner = None
        if opts['no_demo_users']:
            profile = UserProfile.objects.filter(role='manager').select_related('user').first()
            existing_owner = profile.user if profile else User.objects.filter(is_superuser=True).first()
            if existing_owner is None:
                raise CommandError(
                    "No manager or admin account exists yet. Run again without --no-demo-users."
                )

        # 1. wipe the stock data (users, including your admin, are kept)
        Sale.objects.all().delete()
        InventoryLog.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        Medicine.objects.all().delete()

        # 2. demo logins (skipped with --no-demo-users)
        users = {}
        if existing_owner is not None:
            users['manager'] = existing_owner
        else:
            for (username, password), role in ((MANAGER, 'manager'), (STAFF, 'staff')):
                user, _ = User.objects.get_or_create(username=username)
                user.set_password(password)
                user.save()
                UserProfile.objects.update_or_create(user=user, defaults={'role': role})
                users[role] = user

        # 3. batches, each with its first line in the history
        medicines = {}
        for name, batch, stock, days, price, reorder, _ in DEMO:
            med = Medicine.objects.create(
                name=name, batch_number=batch, stock_quantity=stock,
                expiry_date=today + timedelta(days=days), price=Decimal(price),
                reorder_level=reorder, added_by=users['manager'],
            )
            medicines.setdefault(name, med)
            log_change(med, 'CREATE', 0, stock, 'Initial stock (demo data)', users['manager'])

        # 4. simulated sales history (rows with no seller, so they are easy to recognise)
        rng = random.Random(42)
        weekday = [1.1, 1.0, 1.0, 1.0, 1.2, 1.3, 0.6]   # Mon..Sun
        base_by_name = {}
        for name, _, _, _, _, _, avg in DEMO:
            base_by_name[name] = max(base_by_name.get(name, 0), avg)

        rows = []
        for name, avg in base_by_name.items():
            if avg <= 0:
                continue
            for i in range(opts['days'], 0, -1):
                day = today - timedelta(days=i)
                expected = avg * weekday[day.weekday()]
                qty = max(0, round(rng.gauss(expected, expected ** 0.5 + 0.5)))
                if qty:
                    rows.append(Sale(
                        medicine=medicines[name], medicine_name=name, quantity=qty,
                        stock_after=999, sale_date=day, sold_by=None,
                    ))
        Sale.objects.bulk_create(rows)

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(DEMO)} batches and {len(rows)} simulated sales."
        ))
        if existing_owner is not None:
            self.stdout.write(f"No accounts were created. Sign in as {existing_owner.username} and add users on the Users panel.")
        else:
            self.stdout.write(f"Manager login:  {MANAGER[0]} / {MANAGER[1]}")
            self.stdout.write(f"Staff login:    {STAFF[0]} / {STAFF[1]}")
