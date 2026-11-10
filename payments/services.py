from django.core.exceptions import ValidationError
from .models import Charge
from accounts.permissions import contractor_scope


def close_charge(loan):
    if not loan.closed_at or loan.items.filter(returned_at=None).exists():
        raise ValidationError("Debes devolver todas las herramientas.")
    amount = 0
    for line in loan.items.all():
        duration = line.returned_at - loan.issued_at
        micros = (
            duration.days * 86400000000
            + duration.seconds * 1000000
            + duration.microseconds
        )
        days = max(1, (micros + 86400000000 - 1) // 86400000000)
        amount += line.daily_rate * days
    charge, _ = Charge.objects.get_or_create(loan=loan, defaults={"amount": amount})
    return charge


def visible_charges(user):
    return contractor_scope(
        user,
        Charge.objects.select_related("loan__contractor").order_by("-pk"),
        "loan__contractor_id",
    )


import uuid
from urllib.parse import urlsplit
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import PermissionDenied
from .models import PaymentAttempt
from .gateway import WebpayGateway

ACTIVE = ("CREATING", "PENDING", "UNKNOWN")
TERMINAL = ("APPROVED", "REJECTED", "CANCELLED", "EXPIRED")


def _allowed(charge, actor):
    if (
        not actor.is_authenticated
        or not actor.is_active
        or not actor.contractor_id
        or actor.contractor_id != charge.loan.contractor_id
    ):
        raise PermissionDenied("Solo el contratista titular puede iniciar este pago.")


def start_payment(*, charge_id, actor):
    if settings.WEBPAY_ENV != "integration":
        raise ValidationError("Solo integración.")
    with transaction.atomic():
        charge = (
            Charge.objects.select_for_update().select_related("loan").get(pk=charge_id)
        )
        _allowed(charge, actor)
        if charge.paid_at:
            raise ValidationError("Este cargo ya está pagado.")
        if charge.attempts.filter(status__in=ACTIVE).exists():
            raise ValidationError(
                "Ya existe un intento pendiente. Consulta su estado antes de volver a pagar."
            )
        attempt = PaymentAttempt.objects.create(
            charge=charge, amount=charge.amount, order=uuid.uuid4().hex[:26]
        )
    try:
        result = WebpayGateway().create(
            buy_order=attempt.order,
            session_id=str(attempt.session_id),
            amount=attempt.amount,
            return_url=settings.PUBLIC_BASE_URL + "/payments/return/",
        )
        url = result["url"]
        token = result["token"]
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname != "webpay3gint.transbank.cl"
            or parts.username
            or parts.password
            or not token
            or len(token) > 200
        ):
            raise ValueError("Respuesta inválida")
        attempt.token = token
        attempt.redirect_url = url
        attempt.status = "PENDING"
        attempt.save(update_fields=["token", "redirect_url", "status", "updated_at"])
    except Exception:
        # La creación puede haber llegado al proveedor: no liberar el cargo para otro intento.
        attempt.status = "UNKNOWN"
        attempt.save(update_fields=["status", "updated_at"])
    return attempt


def _apply(attempt_id, data):
    charge_id = PaymentAttempt.objects.values_list("charge_id", flat=True).get(
        pk=attempt_id
    )
    with transaction.atomic():
        charge = Charge.objects.select_for_update().get(pk=charge_id)
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt_id)
        if attempt.status in TERMINAL:
            return attempt
        valid = (
            isinstance(data, dict)
            and str(data.get("buy_order")) == attempt.order
            and str(data.get("session_id")) == str(attempt.session_id)
            and str(data.get("amount")) == str(attempt.amount)
        )
        if not valid:
            attempt.status = "UNKNOWN"
        elif (
            data.get("status") == "AUTHORIZED"
            and data.get("response_code") == 0
            and data.get("authorization_code")
        ):
            attempt.status = "APPROVED"
            attempt.authorization = str(data["authorization_code"])[:30]
            if not charge.paid_at:
                charge.paid_at = timezone.now()
                charge.save(update_fields=["paid_at"])
        elif (
            data.get("status") == "INITIALIZED"
            and attempt.token
            and attempt.redirect_url
        ):
            attempt.status = "PENDING"
        elif data.get("status") == "FAILED":
            attempt.status = "REJECTED"
        elif data.get("status") in ("REVERSED", "NULLIFIED"):
            attempt.status = "CANCELLED"
        elif data.get("status") == "EXPIRED":
            attempt.status = "EXPIRED"
        else:
            attempt.status = "UNKNOWN"
        code = data.get("response_code") if isinstance(data, dict) else None
        attempt.response_code = code if isinstance(code, int) else None
        attempt.save(
            update_fields=["status", "authorization", "response_code", "updated_at"]
        )
        return attempt


def confirm_payment(token):
    attempt = PaymentAttempt.objects.filter(token=token).first() if token else None
    if attempt is None:
        raise ValidationError("No se reconoce este intento de pago.")
    if attempt.status in TERMINAL:
        return attempt
    gateway = WebpayGateway()
    try:
        data = gateway.status(token)
        if data.get("status") == "INITIALIZED":
            try:
                data = gateway.commit(token)
            except Exception:
                data = gateway.status(token)
    except Exception:
        data = {}
    return _apply(attempt.pk, data)


def reconcile_payment(attempt_id):
    attempt = PaymentAttempt.objects.get(pk=attempt_id)
    if attempt.status in TERMINAL:
        return attempt
    if not attempt.token:
        return _apply(attempt.pk, {})
    try:
        data = WebpayGateway().status(attempt.token)
    except Exception:
        data = {}
    return _apply(attempt.pk, data)
