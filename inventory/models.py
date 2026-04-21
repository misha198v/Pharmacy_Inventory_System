from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [('staff', 'Staff'), ('manager', 'Manager')]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Medicine(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    expiry_date = models.DateField()
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # tracks who added

    class Meta:
        ordering = ['expiry_date']

    def __str__(self):
        return self.name

    @property
    def status(self):
        from django.utils import timezone
        today = timezone.now().date()
        days_left = (self.expiry_date - today).days
        if days_left < 0:
            return "EXPIRED"
        elif days_left < 30:
            return "EXPIRING"
        elif self.stock_quantity < self.reorder_level:
            return "REORDER"
        return "OK"

    @property
    def days_until_expiry(self):
        from django.utils import timezone
        today = timezone.now().date()
        return (self.expiry_date - today).days

class InventoryLog(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} - {self.medicine.name}"