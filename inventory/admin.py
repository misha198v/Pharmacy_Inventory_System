from django.contrib import admin
from .models import InventoryLog, Medicine, UserProfile

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    # This shows your notebook logic columns directly in the dashboard!
    list_display = ('name', 'stock_quantity', 'expiry_date', 'status', 'days_until_expiry')
    list_filter = ('expiry_date',)
    search_fields = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'action', 'performed_by', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('medicine__name', 'performed_by__username')
    readonly_fields = ('timestamp',)