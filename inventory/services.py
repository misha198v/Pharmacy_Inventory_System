from datetime import timedelta
from django.db import transaction
from django.db.models import Sum, Avg
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import BatchStock, StockMovement, InventoryLog, Medicine


def get_stock_batches_for_medicine(medicine_id):
    return (
        BatchStock.objects
        .filter(medicine_id=medicine_id, quantity__gt=0)
        .order_by('expiry_date', 'received_at')
    )


def receive_stock(medicine_id, batch_number, expiry_date, quantity, performed_by, cost_price=0, supplier="", notes=""):
    if quantity <= 0:
        raise ValidationError("Received quantity must be greater than zero.")

    medicine = Medicine.objects.get(id=medicine_id)

    batch, created = BatchStock.objects.get_or_create(
        medicine=medicine,
        batch_number=batch_number,
        defaults={
            "expiry_date": expiry_date,
            "quantity": 0,
            "cost_price": cost_price,
            "supplier": supplier,
        },
    )

    if not created and batch.expiry_date != expiry_date:
        batch.expiry_date = expiry_date

    old_quantity = batch.quantity
    batch.quantity += quantity
    batch.cost_price = cost_price or batch.cost_price
    batch.supplier = supplier or batch.supplier
    batch.save()

    StockMovement.objects.create(
        medicine=medicine,
        batch=batch,
        movement_type='RECEIVE',
        quantity=quantity,
        performed_by=performed_by,
        notes=notes or "Stock received",
    )

    InventoryLog.objects.create(
        medicine=medicine,
        medicine_name=medicine.name,
        batch=batch,
        action='RECEIVE',
        stock_before=old_quantity,
        stock_after=batch.quantity,
        reason=notes or "Stock received",
        performed_by=performed_by,
    )

    medicine.stock_quantity = medicine.total_stock
    medicine.save(update_fields=['stock_quantity'])

    return batch


def sell_medicine(medicine_id, quantity, performed_by, reason=""):
    if quantity <= 0:
        raise ValidationError("Sale quantity must be greater than zero.")

    medicine = Medicine.objects.get(id=medicine_id)

    batches = get_stock_batches_for_medicine(medicine_id)
    remaining = quantity

    if not batches.exists():
        raise ValidationError("No stock available for this medicine.")

    with transaction.atomic():
        for batch in batches:
            if remaining <= 0:
                break

            used = min(batch.quantity, remaining)
            batch.quantity -= used
            batch.save()

            StockMovement.objects.create(
                medicine=medicine,
                batch=batch,
                movement_type='SALE',
                quantity=used,
                performed_by=performed_by,
                notes=reason or "Sale",
            )

            InventoryLog.objects.create(
                medicine=medicine,
                medicine_name=medicine.name,
                batch=batch,
                action='SALE',
                stock_before=batch.quantity + used,
                stock_after=batch.quantity,
                reason=reason or "Sale",
                performed_by=performed_by,
            )

            remaining -= used

        if remaining > 0:
            raise ValidationError("Not enough stock available to fulfill this sale.")

    medicine.stock_quantity = medicine.total_stock
    medicine.save(update_fields=['stock_quantity'])

    return True


def forecast_reorder_for_medicine(medicine_id):
    medicine = Medicine.objects.get(id=medicine_id)

    current_stock = medicine.total_stock

    sales = StockMovement.objects.filter(
        medicine=medicine,
        movement_type='SALE',
        created_at__gte=timezone.now() - timedelta(days=90)
    )

    avg_daily_sales = sales.aggregate(avg=Avg('quantity'))['avg'] or 0
    projected_28_days = avg_daily_sales * 28 if avg_daily_sales else 0

    safety_stock = max(7, int((avg_daily_sales or 0) * 7))

    near_expiry_stock = (
        BatchStock.objects
        .filter(
            medicine=medicine,
            quantity__gt=0,
            expiry_date__lte=timezone.now().date() + timedelta(days=30)
        )
        .aggregate(total=Sum('quantity'))['total'] or 0
    )

    recommended_purchase = max(0, projected_28_days + safety_stock - current_stock)

    if near_expiry_stock > 0:
        recommended_purchase = max(0, recommended_purchase - near_expiry_stock)

    return {
        "medicine_id": medicine.id,
        "medicine_name": medicine.name,
        "current_stock": current_stock,
        "avg_daily_sales": float(avg_daily_sales or 0),
        "projected_28_days": projected_28_days,
        "safety_stock": safety_stock,
        "near_expiry_stock": near_expiry_stock,
        "recommended_purchase": recommended_purchase,
    }


def get_expiring_batches(medicine_id=None):
    queryset = BatchStock.objects.filter(quantity__gt=0)

    if medicine_id:
        queryset = queryset.filter(medicine_id=medicine_id)

    return queryset.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30)
    ).order_by('expiry_date')