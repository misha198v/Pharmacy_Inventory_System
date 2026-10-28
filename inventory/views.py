from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Lower
from django.utils import timezone

from .permissions import IsManagerOrReadOnly
from .models import Medicine, UserProfile, InventoryLog, NEAR_EXPIRY_DAYS
from .serializers import MedicineSerializer, UserSerializer, InventoryLogSerializer


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


def _history(medicine_id):
    return InventoryLogSerializer(
        InventoryLog.objects.filter(medicine_id=medicine_id), many=True
    ).data


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

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        return Response(_history(pk))


# STOCK RULES
# A "medicine" is every batch that shares a name. Each row in the table is one
# batch, so questions like "is it low on stock?" must be answered for the whole
# medicine, not row by row (a nearly empty old batch does not mean the shelf is
# running out when a big newer batch is waiting behind it).

def _stock_by_medicine(today):
    """{lowercase name: {'sellable': units not expired, 'reorder_level': highest level set}}"""
    groups = {}
    rows = Medicine.objects.values('name', 'stock_quantity', 'expiry_date', 'reorder_level')
    for r in rows:
        g = groups.setdefault(r['name'].lower(), {'sellable': 0, 'reorder_level': 0})
        if r['expiry_date'] >= today:
            g['sellable'] += r['stock_quantity']
        g['reorder_level'] = max(g['reorder_level'], r['reorder_level'])
    return groups


def _low_stock_names(groups):
    return {name for name, g in groups.items() if g['sellable'] < g['reorder_level']}


def _stock_value(queryset):
    return queryset.aggregate(
        total=Sum(
            F('price') * F('stock_quantity'),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )['total'] or 0


# DASHBOARD & SUMMARY VIEWS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    today = timezone.localdate()
    groups = _stock_by_medicine(today)

    in_stock = Medicine.objects.filter(stock_quantity__gt=0)
    sellable = in_stock.filter(expiry_date__gte=today)
    expired = in_stock.filter(expiry_date__lt=today)
    expiring = sellable.filter(expiry_date__lt=today + timedelta(days=NEAR_EXPIRY_DAYS))

    return Response({
        'total_medicines': len(groups),                      # distinct medicines
        'total_batches': Medicine.objects.count(),           # rows in the inventory table
        'total_stock_value': _stock_value(sellable),         # sellable stock only
        'expired_stock_value': _stock_value(expired),        # money sitting on the shelf, lost
        'expired_units': expired.aggregate(t=Sum('stock_quantity'))['t'] or 0,
        'low_stock_count': len(_low_stock_names(groups)),
        'expiring_soon_count': expiring.count(),             # batches with stock, not yet expired
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_medicines(request):
    """Batches of every medicine whose total sellable stock is below its reorder level."""
    names = _low_stock_names(_stock_by_medicine(timezone.localdate()))
    medicines = (
        Medicine.objects.annotate(lname=Lower('name'))
        .filter(lname__in=names)
        .fefo_order()
    )
    return Response(MedicineSerializer(medicines, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expired_medicines(request):
    """Expired batches that still have units on the shelf (units to remove or write off)."""
    medicines = (
        Medicine.objects.filter(stock_quantity__gt=0, expiry_date__lt=timezone.localdate())
        .fefo_order()
    )
    return Response(MedicineSerializer(medicines, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def near_expiry_medicines(request):
    """In-date batches with stock that expire within NEAR_EXPIRY_DAYS."""
    today = timezone.localdate()
    medicines = (
        Medicine.objects.sellable(today)
        .filter(expiry_date__lt=today + timedelta(days=NEAR_EXPIRY_DAYS))
        .fefo_order()
    )
    return Response(MedicineSerializer(medicines, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def medicine_history(request, medicine_id):
    return Response(_history(medicine_id))