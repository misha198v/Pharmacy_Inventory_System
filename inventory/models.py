from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
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
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01, message="Price must be greater than 0.")]
    )
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0, message="Cost price cannot be negative.")]
    )
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0, message="Stock quantity cannot be negative.")]
    )
    unit = models.CharField(max_length=50, blank=True, null=True)
    reorder_level = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0, message="Reorder level cannot be negative.")]
    )
    expiry_date = models.DateField()
    manufacture_date = models.DateField(blank=True, null=True)
    supplier = models.CharField(max_length=200, blank=True, null=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    objects = MedicineQuerySet.as_manager()

    class Meta:
        ordering = ['expiry_date']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'batch_number'],
                name='unique_medicine_batch',
                condition=models.Q(batch_number__isnull=False),
            )
        ]

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
        elif self.stock_quantity < self.reorder_level:
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
        Medicine, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='logs'
    )
    medicine_name = models.CharField(max_length=200)  # kept even if medicine is deleted
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    stock_before = models.IntegerField(null=True, blank=True)
    stock_after = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
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