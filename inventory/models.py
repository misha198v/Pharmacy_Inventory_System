from django.db import models
from django.db import models
from django.contrib.auth.models import User

class InventoryLog(models.Model):
    medicine = models.ForeignKey(Medicine, on_激on_delete=models.CASCADE)
    action = models.CharField(max_length=50) # e.g., "Added 50 units"
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class Medicine(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    expiry_date = models.DateField()

    def __str__(self):
        return self.name
    
    # ADD EVERYTHING BELOW THIS LINE TO YOUR CLASS:

    class Meta:
        ordering = ['expiry_date']

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


