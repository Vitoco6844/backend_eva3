"""Liquidación inmutable de períodos históricos y saldos por retraso."""

from datetime import timezone as utc_timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Charge


def units(start, end, minimum=0):
    delta = end.astimezone(utc_timezone.utc) - start.astimezone(utc_timezone.utc)
    micros = delta.days * 86400000000 + delta.seconds * 1000000 + delta.microseconds
    return max(minimum, (micros + 86400000000 - 1) // 86400000000)


@transaction.atomic
def close_charge(loan):
    from rentals.models import Loan

    loan = Loan.objects.select_for_update().get(pk=loan.pk)
    if not loan.closed_at or loan.items.filter(returned_at=None).exists():
        raise ValidationError("Debes devolver todas las herramientas.")
    prepaid = loan.billing_mode == "PREPAID"
    if (
        prepaid
        and not loan.charges.filter(kind="INITIAL", paid_at__isnull=False).exists()
    ):
        raise ValidationError(
            "El préstamo de pago previo no tiene su cargo inicial confirmado."
        )
    amount = sum(
        line.daily_rate
        * units(
            loan.due_at if prepaid else loan.issued_at,
            line.returned_at,
            0 if prepaid else 1,
        )
        for line in loan.items.all()
    )
    kind = "EXTRA" if prepaid else "LEGACY"
    if amount == 0:
        return None
    charge, _ = Charge.objects.get_or_create(
        loan=loan, kind=kind, defaults={"amount": amount}
    )
    return charge


def billing_summary(loan):
    charges = list(loan.charges.filter(voided_at=None))
    return {
        "initial": sum(c.amount for c in charges if c.kind == "INITIAL"),
        "extra": sum(c.amount for c in charges if c.kind == "EXTRA"),
        "paid": sum(c.amount for c in charges if c.paid_at),
        "outstanding": sum(c.amount for c in charges if not c.paid_at),
        "total": sum(c.amount for c in charges),
    }
