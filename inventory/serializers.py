from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Medicine, UserProfile

class MedicineSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    added_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = ['id', 'name', 'description', 'price', 'stock_quantity',
                  'reorder_level', 'expiry_date', 'status', 'days_until_expiry', 'added_by_username']

    def get_added_by_username(self, obj):
        return obj.added_by.username if obj.added_by else "Unknown"

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'role']

    def get_role(self, obj):
        try:
            return obj.userprofile.role
        except:
            return 'staff'