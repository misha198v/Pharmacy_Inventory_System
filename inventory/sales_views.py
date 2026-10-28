from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import InventoryLog, Medicine, Sale


def _is_manager(user):
    # Same rule as login_view: no profile means staff.
    profile = getattr(user, 'userprofile', None)
    return bool(profile and profile.role == 'manager')


def _truthy(value):
    return value is True or str(value).strip().lower() in ('1', 'true', 'yes')


def plan_allocations(batches, quantity, first_batch=None):
    """Decide how many units to take from each batch. Changes nothing.

    `batches` must already be in FEFO order (earliest expiry first).
    `first_batch` is only used for a manager override: that batch goes
    first, then the rest follow in FEFO order.
    Returns a list of (batch, units_to_take).
    """
    ordered = list(batches)
    if first_batch is not None:
        ordered = [first_batch] + [b for b in ordered if b.pk != first_batch.pk]

    plan = []
    remaining = quantity
    for batch in ordered:
        if remaining == 0:
            break
        take = min(remaining, batch.stock_quantity)
        plan.append((batch, take))
        remaining -= take
    return plan


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sales(request):
    # GET: the 50 most recent sales, newest first
    if request.method == 'GET':
        recent = Sale.objects.select_related('sold_by', 'medicine')[:50]
        return Response([
            {
                'id': s.id,
                'medicine_name': s.medicine_name,
                'batch_number': s.medicine.batch_number if s.medicine else None,
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

    # dry_run=true shows what the sale WOULD do (the "Review sale" step)
    # without changing any stock.
    dry_run = _truthy(request.data.get('dry_run'))

    # Manager override: sell from a chosen batch ahead of the earliest-expiring
    # one (for example when that batch is damaged or cannot be reached).
    override_id = request.data.get('override_batch_id')
    reason = str(request.data.get('reason', '')).strip()
    if override_id in (None, ''):
        override_id = None
    else:
        if not _is_manager(request.user):
            return Response(
                {'detail': 'Only a manager can sell out of expiry order.'},
                status=403,
            )
        if not reason:
            return Response(
                {'detail': 'Give a reason when selling out of expiry order.'},
                status=400,
            )
        try:
            override_id = int(override_id)
        except (TypeError, ValueError):
            return Response({'detail': 'override_batch_id must be a number.'}, status=400)

    today = timezone.localdate()

    # Either every batch is updated or none is (no half-finished sales).
    with transaction.atomic():
        batches = list(
            Medicine.objects.select_for_update()
            .filter(name__iexact=name)
            .sellable(today)
            .fefo_order()
        )

        available = sum(b.stock_quantity for b in batches)
        if available == 0:
            in_stock = Medicine.objects.filter(name__iexact=name)
            if not in_stock.exists():
                return Response({'detail': f"'{name}' was not found."}, status=400)
            expired_units = (
                in_stock.filter(stock_quantity__gt=0, expiry_date__lt=today)
                .aggregate(total=Sum('stock_quantity'))['total'] or 0
            )
            note = f" ({expired_units} expired units cannot be sold)" if expired_units else ""
            return Response(
                {'detail': f"No sellable stock for '{name}'{note}."},
                status=400,
            )
        if available < quantity:
            return Response(
                {'detail': f"Only {available} units of '{name}' can be sold, you asked for {quantity}."},
                status=400,
            )

        first = None
        if override_id is not None:
            first = next((b for b in batches if b.pk == override_id), None)
            if first is None:
                return Response(
                    {'detail': 'That batch cannot be sold: it is expired, empty, '
                               'or not a batch of this medicine.'},
                    status=400,
                )
        # Only counts as an override if it really changes the FEFO order.
        is_override = first is not None and first.pk != batches[0].pk
        if not is_override:
            first = None

        plan = plan_allocations(batches, quantity, first)
        log_reason = f"FEFO override: {reason}"[:255] if is_override else ''

        allocations = []
        for batch, take in plan:
            stock_before = batch.stock_quantity
            stock_after = stock_before - take

            if not dry_run:
                batch.stock_quantity = stock_after
                batch.save(update_fields=['stock_quantity'])
                Sale.objects.create(
                    medicine=batch,
                    medicine_name=batch.name,
                    quantity=take,
                    stock_after=stock_after,
                    sale_date=today,
                    sold_by=request.user,
                )
                InventoryLog.objects.create(
                    medicine=batch,
                    medicine_name=batch.name,
                    action='SALE',
                    stock_before=stock_before,
                    stock_after=stock_after,
                    reason=log_reason,
                    performed_by=request.user,
                )

            allocations.append({
                'batch_id': batch.pk,
                'batch_number': batch.batch_number,
                'expiry_date': str(batch.expiry_date),
                'quantity': take,
                'stock_after': stock_after,
            })

    return Response(
        {
            'medicine': name,
            'sold': quantity,
            'allocations': allocations,
            'override': is_override,
            'dry_run': dry_run,
        },
        status=200 if dry_run else 201,
    )