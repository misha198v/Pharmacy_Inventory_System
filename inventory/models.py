from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum


class UserProfile(models.Model):
    ROLE_CHOICES = [('staff', 'Staff'), ('manager', 'Manager')]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Medicine(models.Model):
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
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

    # Legacy compatibility field, kept for older code.
    # Real stock should now come from the related BatchStock records.
    stock_quantity = models.IntegerField(default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        total = self.batches.aggregate(total=Sum('quantity'))['total']
        return total or 0

    @property
    def nearest_expiry_date(self):
        batch = self.batches.filter(quantity__gt=0).order_by('expiry_date').first()
        return batch.expiry_date if batch else None

    @property
    def days_until_expiry(self):
        expiry = self.nearest_expiry_date
        if not expiry:
            return None
        today = timezone.now().date()
        return (expiry - today).days

    @property
    def status(self):
        today = timezone.now().date()
        total = self.total_stock

        if total <= 0:
            return "OUT_OF_STOCK"

        expiring_batches = self.batches.filter(
            quantity__gt=0,
            expiry_date__gte=today,
            expiry_date__lte=today + timezone.timedelta(days=30)
        )

        if expiring_batches.exists():
            return "EXPIRING"

        if total <= self.reorder_level:
            return "REORDER"

        return "OK"


class BatchStock(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    manufacture_date = models.DateField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0, message="Cost price cannot be negative.")]
    )
    supplier = models.CharField(max_length=200, blank=True, null=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expiry_date', 'received_at']
        constraints = [
            models.UniqueConstraint(
                fields=['medicine', 'batch_number'],
                name='unique_batch_number_per_medicine'
            )
        ]

    def __str__(self):
        return f"{self.medicine.name} - {self.batch_number}"

    @property
    def days_until_expiry(self):
        today = timezone.now().date()
        return (self.expiry_date - today).days


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('RECEIVE', 'Receive'),
        ('SALE', 'Sale'),
        ('ADJUSTMENT', 'Adjustment'),
        ('WRITE_OFF', 'Write Off'),
        ('RETURN', 'Return'),
    ]

    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='stock_movements')
    batch = models.ForeignKey(BatchStock, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medicine.name} - {self.movement_type} - {self.quantity}"


class InventoryLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('RECEIVE', 'Received'),
        ('SALE', 'Sold'),
        ('ADJUSTMENT', 'Adjusted'),
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
        return f"{self.action} - {self.medicine_name}"