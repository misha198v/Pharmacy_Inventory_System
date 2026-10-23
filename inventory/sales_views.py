from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import log_change
from .models import Medicine, Sale


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sales(request):
    # GET: the 50 most recent sales, newest first
    if request.method == 'GET':
        recent = Sale.objects.select_related('sold_by')[:50]
        return Response([
            {
                'id': s.id,
                'medicine_name': s.medicine_name,
                'quantity': s.quantity,
                'stock_after': s.stock_after,
                'sale_date': str(s.sale_date),
                'sold_by': s.sold_by.username if s.sold_by else None,
            }
            for s in recent
        ])

    # POST: record a sale. The system picks the batches (FEFO), not the user.
    name = str(request.data.get('medicine_name', '')).strip()
    try:
        quantity = int(request.data.get('quantity'))
    except (TypeError, ValueError):
        quantity = 0

    if not name or quantity < 1:
        return Response(
            {'detail': 'Provide medicine_name and a quantity of at least 1.'},
            status=400,
        )

    today = timezone.localdate()

    # Either every batch is updated or none is (no half-finished sales).
    with transaction.atomic():
        batches = list(
            Medicine.objects.select_for_update()
            .filter(name__iexact=name, stock_quantity__gt=0)
            .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
            .order_by(F('expiry_date').asc(nulls_last=True), 'id')
        )

        available = sum(b.stock_quantity for b in batches)
        if available == 0:
            return Response(
                {'detail': f"No sellable stock for '{name}'. Expired batches are never sold."},
                status=400,
            )
        if available < quantity:
            return Response(
                {'detail': f"Only {available} units of '{name}' can be sold, you asked for {quantity}."},
                status=400,
            )

        remaining = quantity
        allocations = []
        for batch in batches:
            if remaining == 0:
                break
            take = min(remaining, batch.stock_quantity)
            stock_before = batch.stock_quantity
            batch.stock_quantity -= take
            batch.save(update_fields=['stock_quantity'])

            Sale.objects.create(
                medicine=batch,
                medicine_name=batch.name,
                quantity=take,
                stock_after=batch.stock_quantity,
                sale_date=today,
                sold_by=request.user,
            )
            # the audit trail: one line per batch touched
            log_change(
                batch, 'UPDATE', stock_before, batch.stock_quantity,
                f'Sale of {take} (FEFO)', request.user,
            )
            allocations.append({
                'batch_number': batch.batch_number,
                'expiry_date': str(batch.expiry_date) if batch.expiry_date else None,
                'quantity': take,
                'stock_after': batch.stock_quantity,
            })
            remaining -= take

    return Response(
        {'medicine': name, 'sold': quantity, 'allocations': allocations},
        status=201,
    )
