from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Medicine, UserProfile, InventoryLog, BatchStock, StockMovement


class MedicineSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    total_stock = serializers.ReadOnlyField()
    added_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
            'id',
            'name',
            'generic_name',
            'category',
            'description',
            'price',
            'cost_price',
            'unit',
            'reorder_level',
            'lead_time_days',
            'supplier',
            'added_by',
            'added_by_username',
            'stock_quantity',
            'total_stock',
            'status',
            'days_until_expiry',
        ]

    def get_added_by_username(self, obj):
        return obj.added_by.username if obj.added_by else "Unknown"


class BatchStockSerializer(serializers.ModelSerializer):
    medicine_name = serializers.SerializerMethodField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = BatchStock
        fields = [
            'id',
            'medicine',
            'medicine_name',
            'batch_number',
            'expiry_date',
            'manufacture_date',
            'quantity',
            'cost_price',
            'supplier',
            'received_at',
            'days_until_expiry',
        ]

    def get_medicine_name(self, obj):
        return obj.medicine.name if obj.medicine else None


class StockMovementSerializer(serializers.ModelSerializer):
    medicine_name = serializers.SerializerMethodField()
    performed_by_username = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            'id',
            'medicine',
            'medicine_name',
            'batch',
            'movement_type',
            'quantity',
            'performed_by',
            'performed_by_username',
            'notes',
            'created_at',
        ]

    def get_medicine_name(self, obj):
        return obj.medicine.name if obj.medicine else None

    def get_performed_by_username(self, obj):
        return obj.performed_by.username if obj.performed_by else "Unknown"


class InventoryLogSerializer(serializers.ModelSerializer):
    performed_by_username = serializers.SerializerMethodField()

    class Meta:
        model = InventoryLog
        fields = [
            'id',
            'medicine',
            'medicine_name',
            'batch',
            'action',
            'stock_before',
            'stock_after',
            'reason',
            'performed_by',
            'performed_by_username',
            'timestamp',
        ]

    def get_performed_by_username(self, obj):
        return obj.performed_by.username if obj.performed_by else "Unknown"


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'role']

    def get_role(self, obj):
        try:
            return obj.userprofile.role
        except Exception:
            return 'staff'