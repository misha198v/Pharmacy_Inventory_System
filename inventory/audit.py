from .models import InventoryLog


def _action_value(label):
    """Return the value your InventoryLog stores for CREATE / UPDATE / DELETE.

    It looks the value up in the field's own choices, so it works whether
    your model stores 'CREATE' or 'create'.
    """
    for value, name in InventoryLog._meta.get_field('action').choices:
        if str(value).upper() == label or str(name).upper() == label:
            return value
    return label


def log_change(medicine, action, stock_before, stock_after, reason, user):
    """Write one line in the audit trail (who changed which batch, from what to what, and why)."""
    InventoryLog.objects.create(
        medicine=medicine,
        medicine_name=medicine.name,
        action=_action_value(action),
        stock_before=stock_before,
        stock_after=stock_after,
        reason=reason,
        performed_by=user,
    )
