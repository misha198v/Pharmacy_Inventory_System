from collections import defaultdict
from datetime import timedelta
from statistics import mean

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import log_change
from .forecast import HISTORY_DAYS, daily_series
from .models import InventoryLog, Medicine, PurchaseOrder
from .permissions import IsManager

# Details a new batch inherits from the medicine's latest batch when an order is received.
COPY_FIELDS = (
    'generic_name', 'category', 'unit', 'supplier', 'description',
    'price', 'cost_price', 'reorder_level',
)


def _manager_only(request):
    """Return a 403 response if the user is not a manager, otherwise None."""
    if not IsManager().has_permission(request, None):
        return Response({'detail': 'Only managers can do this.'}, status=403)
    return None


def _order_dict(o):
    return {
        'id': o.id,
        'medicine_name': o.medicine_name,
        'quantity': o.quantity,
        'supplier': o.supplier,
        'status': o.status,
        'ordered_by': o.ordered_by.username if o.ordered_by else None,
        'ordered_at': o.ordered_at.isoformat(),
        'received_at': o.received_at.isoformat() if o.received_at else None,
    }


# ---------- Purchase orders ----------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def orders(request):
    if request.method == 'GET':
        recent = PurchaseOrder.objects.select_related('ordered_by')[:50]
        return Response([_order_dict(o) for o in recent])

    # POST: only managers place orders
    denied = _manager_only(request)
    if denied:
        return denied

    name = str(request.data.get('medicine_name', '')).strip()
    try:
        quantity = int(request.data.get('quantity'))
    except (TypeError, ValueError):
        quantity = 0
    if not name or quantity < 1:
        return Response(
            {'detail': 'Provide medicine_name and a quantity of at least 1.'}, status=400
        )

    known = Medicine.objects.filter(name__iexact=name).order_by('-id').first()
    if known is None:
        return Response({'detail': f"'{name}' is not in the inventory."}, status=400)

    supplier = str(request.data.get('supplier', '')).strip()
    if not supplier:
        supplier = str(getattr(known, 'supplier', '') or '')[:200]

    order = PurchaseOrder.objects.create(
        medicine_name=known.name,
        quantity=quantity,
        supplier=supplier,
        ordered_by=request.user,
    )
    return Response(_order_dict(order), status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_order(request, order_id):
    """The delivery arrived: create the new batch and mark the order received."""
    batch_number = str(request.data.get('batch_number', '')).strip()
    try:
        expiry = parse_date(str(request.data.get('expiry_date', '')))
    except ValueError:
        expiry = None

    if not batch_number or expiry is None:
        return Response(
            {'detail': 'A batch number and a valid expiry date (YYYY-MM-DD) are required.'},
            status=400,
        )
    if expiry <= timezone.localdate():
        return Response({'detail': 'The expiry date must be in the future.'}, status=400)

    field_names = {f.name for f in Medicine._meta.get_fields()}

    with transaction.atomic():
        try:
            order = PurchaseOrder.objects.select_for_update().get(pk=order_id)
        except PurchaseOrder.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=404)

        if order.status != 'ORDERED':
            return Response(
                {'detail': f'This order is already {order.status.lower()}.'}, status=400
            )

        template = (
            Medicine.objects.filter(name__iexact=order.medicine_name).order_by('-id').first()
        )
        if template is None:
            return Response({'detail': 'The medicine no longer exists.'}, status=400)

        if Medicine.objects.filter(
            name__iexact=template.name, batch_number=batch_number
        ).exists():
            return Response(
                {'detail': f"Batch '{batch_number}' of {template.name} already exists."},
                status=400,
            )

        inherited = {f: getattr(template, f) for f in COPY_FIELDS if f in field_names}
        batch = Medicine.objects.create(
            name=template.name,
            batch_number=batch_number,
            stock_quantity=order.quantity,
            expiry_date=expiry,
            added_by=request.user,
            **inherited,
        )

        order.status = 'RECEIVED'
        order.received_at = timezone.now()
        order.received_batch = batch
        order.save(update_fields=['status', 'received_at', 'received_batch'])

        log_change(
            batch, 'CREATE', 0, order.quantity,
            f'Received purchase order #{order.id}', request.user,
        )

    return Response(
        {
            'order': _order_dict(order),
            'batch': {
                'id': batch.id,
                'name': batch.name,
                'batch_number': batch.batch_number,
                'stock_quantity': batch.stock_quantity,
                'expiry_date': str(batch.expiry_date),
            },
        },
        status=201,
    )


# ---------- Expired stock ----------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def write_off(request, medicine_id):
    """A manager removes the stock of an EXPIRED batch, with the reason on record."""
    denied = _manager_only(request)
    if denied:
        return denied

    reason = str(request.data.get('reason', '')).strip() or 'Expired stock written off'
    today = timezone.localdate()

    with transaction.atomic():
        try:
            med = Medicine.objects.select_for_update().get(pk=medicine_id)
        except Medicine.DoesNotExist:
            return Response({'detail': 'Medicine not found.'}, status=404)

        # Only expired batches, so this cannot be used to make good stock disappear.
        if med.expiry_date is None or med.expiry_date >= today:
            return Response({'detail': 'Only expired batches can be written off.'}, status=400)
        if med.stock_quantity == 0:
            return Response({'detail': 'This batch has no stock left.'}, status=400)

        before = med.stock_quantity
        med.stock_quantity = 0
        med.save(update_fields=['stock_quantity'])
        log_change(med, 'UPDATE', before, 0, reason, request.user)

    return Response({'id': med.id, 'written_off': before})


# ---------- History and chart ----------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history(request):
    """The audit trail for every batch of one medicine, newest first."""
    name = request.query_params.get('name', '').strip()
    if not name:
        return Response({'detail': 'Provide ?name=<medicine name>.'}, status=400)

    logs = (
        InventoryLog.objects.filter(medicine_name__iexact=name)
        .select_related('performed_by', 'medicine')
        .order_by('-timestamp')[:100]
    )
    return Response([
        {
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'action': str(log.action).upper(),
            'batch_number': log.medicine.batch_number if log.medicine else None,
            'stock_before': log.stock_before,
            'stock_after': log.stock_after,
            'reason': log.reason,
            'performed_by': log.performed_by.username if log.performed_by else None,
        }
        for log in logs
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def forecast_chart(request):
    """Daily sales for the last 28 days plus the forecast for the next days (for the chart)."""
    name = request.query_params.get('name', '').strip()
    known = Medicine.objects.filter(name__iexact=name).order_by('-id').first() if name else None
    if known is None:
        return Response({'detail': 'Medicine not found.'}, status=404)

    try:
        ahead = max(1, min(int(request.query_params.get('ahead_days', 14)), 30))
    except ValueError:
        ahead = 14

    today = timezone.localdate()
    values = daily_series().get(known.name.lower()) or [0] * HISTORY_DAYS
    start = today - timedelta(days=len(values))

    history_points = [
        {'date': str(start + timedelta(days=i)), 'units': v} for i, v in enumerate(values)
    ]

    # Forecast = the average of the same weekday over the history window.
    by_weekday = defaultdict(list)
    for i, v in enumerate(values):
        by_weekday[(start + timedelta(days=i)).weekday()].append(v)
    weekday_avg = {w: mean(vs) for w, vs in by_weekday.items()}
    overall = mean(values)

    forecast_points = []
    for i in range(ahead):
        day = today + timedelta(days=i)
        forecast_points.append({
            'date': str(day),
            'units': round(weekday_avg.get(day.weekday(), overall), 1),
        })

    return Response({
        'medicine_name': known.name,
        'history': history_points,
        'forecast': forecast_points,
        'avg_daily': round(overall, 2),
    })
