from rest_framework import serializers
from .models import Medicine

class MedicineSerializer(serializers.ModelSerializer):
    # We explicitly include the properties we added to the model
    status = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Medicine
        # List every field you want to show in your React app
        fields = [
            'id', 
            'name', 
            'description', 
            'price', 
            'stock_quantity', 
            'reorder_level', 
            'expiry_date', 
            'status', 
            'days_until_expiry'
        ]