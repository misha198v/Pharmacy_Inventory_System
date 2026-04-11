from django.contrib import admin
from .models import Medicine

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    # This shows your notebook logic columns directly in the dashboard!
    list_display = ('name', 'stock_quantity', 'expiry_date', 'status', 'days_until_expiry')
    list_filter = ('expiry_date',)
    search_fields = ('name',)