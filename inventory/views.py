from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.db.models import Sum, F
from django.core.exceptions import ValidationError

from .permissions import IsManagerOrReadOnly
from .models import Medicine, InventoryLog, BatchStock
from .serializers import (
    MedicineSerializer,
    InventoryLogSerializer,
    BatchStockSerializer,
    StockMovementSerializer,
)
from .services import (
    sell_medicine,
    receive_stock,
    forecast_reorder_for_medicine,
    get_expiring_batches,
)


class LoginRateThrottle(ScopedRateThrottle):
    scope = 'auth_login'


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
        except Exception:
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

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        logs = InventoryLog.objects.filter(medicine_id=pk)
        serializer = InventoryLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def receive_stock(self, request, pk=None):
        medicine = self.get_object()
        batch_number = request.data.get('batch_number')
        expiry_date = request.data.get('expiry_date')
        quantity = int(request.data.get('quantity', 0))
        cost_price = request.data.get('cost_price', 0)
        supplier = request.data.get('supplier', '')
        notes = request.data.get('notes', '')

        if not batch_number or not expiry_date or quantity <= 0:
            return Response({"detail": "batch_number, expiry_date, and quantity are required."}, status=400)

        try:
            receive_stock(
                medicine_id=medicine.id,
                batch_number=batch_number,
                expiry_date=expiry_date,
                quantity=quantity,
                performed_by=request.user,
                cost_price=cost_price,
                supplier=supplier,
                notes=notes
            )
            return Response({"detail": "Stock received successfully."})
        except ValidationError as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def sell_stock(self, request, pk=None):
        medicine = self.get_object()
        quantity = int(request.data.get('quantity', 0))
        reason = request.data.get('reason', '')

        if quantity <= 0:
            return Response({"detail": "Quantity must be greater than zero."}, status=400)

        try:
            sell_medicine(medicine.id, quantity, request.user, reason)
            return Response({"detail": "Sale processed successfully."})
        except ValidationError as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=True, methods=['get'])
    def batch_stock(self, request, pk=None):
        medicine = self.get_object()
        batches = BatchStock.objects.filter(medicine=medicine).order_by('expiry_date')
        serializer = BatchStockSerializer(batches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def reorder_forecast(self, request, pk=None):
        medicine = self.get_object()
        data = forecast_reorder_for_medicine(medicine.id)
        return Response(data)


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
def low_stock_medicines(request):
    medicines = [m for m in Medicine.objects.all() if m.status == 'REORDER']
    serializer = MedicineSerializer(medicines, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expired_medicines(request):
    medicines = [m for m in Medicine.objects.all() if m.status == 'EXPIRED']
    serializer = MedicineSerializer(medicines, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def near_expiry_medicines(request):
    medicines = [m for m in Medicine.objects.all() if m.status == 'EXPIRING']
    serializer = MedicineSerializer(medicines, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def medicine_history(request, medicine_id):
    logs = InventoryLog.objects.filter(medicine_id=medicine_id)
    serializer = InventoryLogSerializer(logs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expiring_batches(request):
    batches = get_expiring_batches()
    serializer = BatchStockSerializer(batches, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def medicine_reorder_forecast(request, medicine_id):
    result = forecast_reorder_for_medicine(medicine_id)
    return Response(result)