from .permissions import IsManagerOrReadOnly
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated 
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Medicine, UserProfile, InventoryLog 
from .serializers import MedicineSerializer, UserSerializer, InventoryLogSerializer
from django.db.models import Sum, F 

class LoginRateThrottle(ScopedRateThrottle):
    scope = 'auth_login'


# LOGIN VIEW
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        try:
            role = user.userprofile.role
        except:
            role = 'staff'
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'role': role,
            },
            'token': token.key,
        })
    return Response({'detail': 'Invalid username or password'}, status=401)


# MEDICINE VIEWSET
class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [IsManagerOrReadOnly]

    def perform_create(self, serializer):
        medicine = serializer.save(added_by=self.request.user)
        InventoryLog.objects.create(
            medicine=medicine,
            medicine_name=medicine.name,
            action='CREATE',
            stock_before=None,
            stock_after=medicine.stock_quantity,
            reason=self.request.data.get('reason', ''),
            performed_by=self.request.user,
        )

    def perform_update(self, serializer):
        stock_before = serializer.instance.stock_quantity
        medicine = serializer.save()
        InventoryLog.objects.create(
            medicine=medicine,
            medicine_name=medicine.name,
            action='UPDATE',
            stock_before=stock_before,
            stock_after=medicine.stock_quantity,
            reason=self.request.data.get('reason', ''),
            performed_by=self.request.user,
        )

    def perform_destroy(self, instance):
        InventoryLog.objects.create(
            medicine=None,
            medicine_name=instance.name,
            action='DELETE',
            stock_before=instance.stock_quantity,
            stock_after=None,
            reason=self.request.data.get('reason', ''),
            performed_by=self.request.user,
        )
        instance.delete()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    medicines = Medicine.objects.all()

    total_medicines = medicines.count()

    total_stock_value = medicines.aggregate(
        total=Sum(F('price') * F('stock_quantity'))
    )['total'] or 0

    low_stock_count = sum(1 for m in medicines if m.status == 'REORDER')
    expiring_soon_count = sum(1 for m in medicines if m.status == 'EXPIRING')

    return Response({
        'total_medicines': total_medicines,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock_count,
        'expiring_soon_count': expiring_soon_count,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def medicine_history(request, medicine_id):
    logs = InventoryLog.objects.filter(medicine_id=medicine_id)
    serializer = InventoryLogSerializer(logs, many=True)
    return Response(serializer.data)