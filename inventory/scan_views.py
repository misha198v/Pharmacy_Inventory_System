"""Scanning at the counter.

The worker scans a pack. The system answers with a green or red verdict that
says whether that pack is the one that must be sold next (FEFO).

Two things can identify a pack:
  * the product barcode  -> tells us WHICH MEDICINE it is
  * the batch number     -> tells us WHICH BATCH it is (printed on the pack, or
                            on a label, and typed or scanned in)

When a medicine has only one batch on the shelf, the product barcode is enough.
When it has two or more, the worker must also confirm the batch number on the
pack, so a newer pack can be refused while an older batch still has stock.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import InventoryLog, Medicine
from .sales_views import _is_manager


def _pretty(d):
    return f"{d.day} {d.strftime('%b')} {d.year}"


def _same_batch(a, b):
    """Compare batch numbers ignoring case and spaces ('bn 2301' == 'BN2301')."""
    clean = lambda s: ''.join(str(s or '').split()).upper()
    return clean(a) == clean(b)


def _batch_info(b, units_left=None):
    return {
        'batch_id': b.pk,
        'batch_number': b.batch_number,
        'expiry_date': str(b.expiry_date),
        'expiry_pretty': _pretty(b.expiry_date),
        'units_left': b.stock_quantity if units_left is None else units_left,
    }


def _verdict(ok, status, message, **extra):
    return {'ok': ok, 'status': status, 'message': message, **extra}


def check_scan(name, basket_qty, scanned_batch, today):
    """Decide whether the pack in the worker's hand is the right one.

    `basket_qty` is how many units of this medicine are already in the current
    sale, so the next unit is the next one in FEFO order after those.
    """
    batches = list(Medicine.objects.filter(name__iexact=name).fefo_order())
    if not batches:
        return _verdict(False, 'UNKNOWN_MEDICINE', f"'{name}' is not in the inventory.")
    medicine = batches[0].name

    sellable = list(Medicine.objects.filter(name__iexact=name).sellable(today).fefo_order())
    if not sellable:
        expired_units = sum(b.stock_quantity for b in batches if b.expiry_date < today)
        if expired_units:
            return _verdict(False, 'EXPIRED', f"All remaining {medicine} has expired "
                            f"({expired_units} units). Do not sell it.", medicine=medicine)
        return _verdict(False, 'OUT_OF_STOCK', f"There is no {medicine} in stock.", medicine=medicine)

    # Share the units already in this sale out over the batches in FEFO order.
    left_to_place = basket_qty
    reserved = []
    for b in sellable:
        take = min(left_to_place, b.stock_quantity)
        left_to_place -= take
        reserved.append(take)

    expected_index = next(
        (i for i, b in enumerate(sellable) if reserved[i] < b.stock_quantity), None
    )

    def state(i):
        if expected_index is None or i < expected_index:
            return 'used'
        return 'next' if i == expected_index else 'locked'

    queue = [
        {**_batch_info(b, b.stock_quantity - reserved[i]), 'state': state(i)}
        for i, b in enumerate(sellable)
    ]

    if expected_index is None:
        return _verdict(False, 'OUT_OF_STOCK',
                        f"All {sum(b.stock_quantity for b in sellable)} sellable units of "
                        f"{medicine} are already in this sale.",
                        medicine=medicine, queue=queue)

    expected = sellable[expected_index]
    expected_left = expected.stock_quantity - reserved[expected_index]
    expected_label = (f"batch {expected.batch_number}" if expected.batch_number else "the oldest batch")
    base = {'medicine': medicine, 'expected_batch': queue[expected_index], 'queue': queue}

    # --- Only the product barcode was scanned ---------------------------------
    if scanned_batch is None:
        on_shelf = [b for b in batches if b.stock_quantity > 0]   # could be the pack in hand
        if len(on_shelf) < 2 or not expected.batch_number:
            return _verdict(True, 'OK', f"{medicine}, expires {_pretty(expected.expiry_date)}.", **base)
        return _verdict(
            False, 'CONFIRM_BATCH',
            f"Take {medicine} from {expected_label} (expires {_pretty(expected.expiry_date)}). "
            f"Scan or type the batch number printed on the pack to confirm.",
            **base,
        )

    # --- The batch number on the pack was given -------------------------------
    match = next((b for b in batches if _same_batch(b.batch_number, scanned_batch)), None)
    if match is None:
        return _verdict(False, 'UNKNOWN_BATCH',
                        f"Batch {scanned_batch} is not recorded for {medicine}. Check the number "
                        f"on the pack, or ask a manager to receive this batch.", **base)
    if match.expiry_date < today:
        return _verdict(False, 'EXPIRED',
                        f"This pack (batch {match.batch_number}) expired on "
                        f"{_pretty(match.expiry_date)}. Do not sell it.", **base)
    if match.stock_quantity == 0:
        return _verdict(False, 'BATCH_EMPTY',
                        f"Records show no units left in batch {match.batch_number}. "
                        f"Ask a manager to check the stock count.", **base)
    if match.pk == expected.pk:
        return _verdict(True, 'OK',
                        f"{medicine}, batch {match.batch_number}, "
                        f"expires {_pretty(match.expiry_date)}.", **base)

    match_index = next(i for i, b in enumerate(sellable) if b.pk == match.pk)
    if match_index < expected_index:
        return _verdict(False, 'BATCH_USED_UP',
                        f"All units of batch {match.batch_number} are already counted in this "
                        f"sale. Take {expected_label} next.", **base)
    return _verdict(
        False, 'BLOCKED',
        f"This pack is batch {match.batch_number}. {expected_label[0].upper() + expected_label[1:]} "
        f"({expected_left} left, expires {_pretty(expected.expiry_date)}) must be sold first. "
        f"Put this pack back and take {expected_label}.",
        **base,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scan(request):
    code = str(request.data.get('code') or '').strip()
    typed_name = str(request.data.get('medicine_name') or '').strip()
    batch_number = str(request.data.get('batch_number') or '').strip() or None

    if not code and not typed_name:
        return Response({'detail': 'Scan a pack, or give a medicine name.'}, status=400)

    if code:
        match = Medicine.objects.filter(barcode=code).first()
        if match is None:
            return Response(_verdict(
                False, 'UNKNOWN_CODE',
                "This barcode is not linked to a medicine yet. Choose the medicine it "
                "belongs to and it will be remembered.",
                code=code,
            ))
        name = match.name
    else:
        name = typed_name

    basket = request.data.get('basket')
    try:
        basket_qty = max(0, int(basket.get(name.lower(), 0))) if isinstance(basket, dict) else 0
    except (TypeError, ValueError):
        basket_qty = 0

    return Response(check_scan(name, basket_qty, batch_number, timezone.localdate()))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def link_barcode(request):
    """Manager only: remember which medicine a barcode belongs to."""
    if not _is_manager(request.user):
        return Response({'detail': 'Only a manager can link a barcode to a medicine.'}, status=403)

    code = str(request.data.get('code') or '').strip()
    name = str(request.data.get('medicine_name') or '').strip()
    if not code or not name or len(code) > 64:
        return Response({'detail': 'Give a barcode (up to 64 characters) and a medicine name.'},
                        status=400)

    batches = list(Medicine.objects.filter(name__iexact=name))
    if not batches:
        return Response({'detail': f"'{name}' is not in the inventory."}, status=400)

    other = Medicine.objects.filter(barcode=code).exclude(name__iexact=name).first()
    if other:
        return Response({'detail': f"This barcode is already linked to '{other.name}'."}, status=400)

    with transaction.atomic():
        for b in batches:
            if b.barcode == code:
                continue
            b.barcode = code
            b.save(update_fields=['barcode'])
            InventoryLog.objects.create(
                medicine=b, medicine_name=b.name, action='UPDATE',
                stock_before=b.stock_quantity, stock_after=b.stock_quantity,
                reason=f"Barcode linked: {code}", performed_by=request.user,
            )

    return Response({'medicine': batches[0].name, 'barcode': code, 'batches': len(batches)})