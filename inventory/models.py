from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings

# A batch with fewer days than this left is flagged EXPIRING.
NEAR_EXPIRY_DAYS = 30


class UserProfile(models.Model):
    ROLE_CHOICES = [('staff', 'Staff'), ('manager', 'Manager')]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class MedicineQuerySet(models.QuerySet):
    def sellable(self, today=None):
        """Batches that may be sold: in stock and not expired.

        One shared definition, so the sale screen, the dashboard and the
        reorder suggestions all agree on what 'sellable stock' means.
        """
        today = today or timezone.localdate()
        return self.filter(stock_quantity__gt=0, expiry_date__gte=today)

    def fefo_order(self):
        """Earliest expiry first; id breaks ties so the order is stable."""
        return self.order_by('expiry_date', 'id')


class Medicine(models.Model):
    """One row = one batch of a medicine."""

    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    # The barcode printed on the pack. It identifies the product, so every
    # batch of the same medicine carries the same value.
    barcode = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    description = models.TextField(blank=True, null=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01, message="Price must be greater than 0.")]
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0, message="Cost price cannot be negative.")]
    )

    unit = models.CharField(max_length=50, blank=True, null=True)
    reorder_level = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0, message="Reorder level cannot be negative.")]
    )
    lead_time_days = models.IntegerField(default=7)
    supplier = models.CharField(max_length=200, blank=True, null=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    objects = MedicineQuerySet.as_manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        # Prevent adding a brand-new medicine record with an already-past expiry date.
        # (Existing expired stock is allowed to remain and be flagged. This only
        # blocks creating a new record that's expired from day one.)
        if self.expiry_date and self.expiry_date < timezone.localdate() and not self.pk:
            raise ValidationError({
                'expiry_date': 'Expiry date cannot be in the past for a new medicine entry.'
            })

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def status(self):
        days_left = self.days_until_expiry
        if days_left < 0:
            return "EXPIRED"
        elif days_left < NEAR_EXPIRY_DAYS:
            return "EXPIRING"

        if total <= self.reorder_level:
            return "REORDER"

        return "OK"


class InventoryLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('SALE', 'Sold'),
    ]

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    medicine_name = models.CharField(max_length=200)
    batch = models.ForeignKey(BatchStock, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    stock_before = models.IntegerField(null=True, blank=True)
    stock_after = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} - {self.medicine_name} by {self.performed_by}"


class Sale(models.Model):
    medicine = models.ForeignKey(
        Medicine, on_delete=models.SET_NULL, null=True, related_name='sales'
    )
    medicine_name = models.CharField(max_length=200)   # kept even if the medicine is deleted
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    stock_after = models.IntegerField()                # stock left after this sale
    sale_date = models.DateField(default=timezone.localdate)
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sale_date', '-created_at']
        indexes = [
            # The forecast reads sales by date and medicine name.
            models.Index(fields=['sale_date', 'medicine_name'], name='sale_date_name_idx'),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.medicine_name} on {self.sale_date}"


class DrugInfo(models.Model):
    """Plain-language information about one medicine, written for patients.

    This is the shared drug record: the pharmacy side finds it by medicine name
    or barcode, and the patient page shows it. It holds no stock, price or
    pharmacy data, so it is safe to show to anyone.
    """

    PURPOSE_CHOICES = [
        ('TREATS', 'Treats'),
        ('PREVENTS', 'Prevents'),
        ('RELIEVES', 'Relieves symptoms'),
        ('SUPPLEMENT', 'Supplement'),
    ]

    # Same wording as the medicine in the inventory, e.g. "Amoxicillin 500mg".
    name = models.CharField(max_length=200, unique=True)
    generic_name = models.CharField(max_length=200)
    also_sold_as = models.CharField(max_length=300, blank=True, help_text="Brand names, separated by commas.")
    drug_group = models.CharField(max_length=120, blank=True)
    purpose = models.CharField(max_length=12, choices=PURPOSE_CHOICES)
    purpose_note = models.CharField(max_length=250, blank=True)
    what_it_is_for = models.TextField()
    # The four fields below are bullet lists: write one point per line.
    how_it_is_usually_taken = models.TextField(blank=True, help_text="One point per line.")
    before_you_take_it = models.TextField(blank=True, help_text="One point per line.")
    get_help_if = models.TextField(blank=True, help_text="One point per line.")
    similar_medicines = models.TextField(blank=True, help_text="One medicine per line.")
    # Until a pharmacist signs it off, the patient page shows a "draft" notice.
    reviewed_by = models.CharField(max_length=200, blank=True)
    reviewed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_reviewed(self):
        return bool(self.reviewed_by and self.reviewed_on)


class DrugBarcode(models.Model):
    """A barcode that belongs to a drug, so packs can be recognised even when
    they did not come from this pharmacy's own stock."""

    code = models.CharField(max_length=64, unique=True)
    drug = models.ForeignKey(DrugInfo, on_delete=models.CASCADE, related_name='barcodes')

    def __str__(self):
        return f"{self.code} -> {self.drug.name}"