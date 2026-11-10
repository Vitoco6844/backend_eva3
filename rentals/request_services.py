import hashlib, json, uuid
from datetime import timezone as datetime_timezone
from django.db import transaction
from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from accounts.permissions import can_operate, require_operator, contractor_scope
from inventory.models import Contractor, Asset
from inventory.catalog import available_for_request
from rentals.services import is_delinquent, issue_loan
from .models import RentalRequest, RentalRequestItem


def require_customer(actor):
    if (
        not actor.is_authenticated
        or not actor.is_active
        or actor.role != "CONTRATISTA"
        or can_operate(actor)
        or not actor.contractor_id
    ):
        raise PermissionDenied(
            "Ingresa con una cuenta de cliente asociada a su identificación."
        )


def visible_requests(user):
    return contractor_scope(
        user,
        RentalRequest.objects.select_related(
            "contractor", "requested_by", "loan"
        ).prefetch_related("items__asset"),
    )


def _pending(req):
    if req.status != "PENDIENTE":
        raise ValidationError("Esta solicitud ya fue resuelta.")


def _days(start, end):
    duration = end.astimezone(datetime_timezone.utc) - start.astimezone(
        datetime_timezone.utc
    )
    micros = (
        duration.days * 86400000000 + duration.seconds * 1000000 + duration.microseconds
    )
    return max(1, (micros + 86400000000 - 1) // 86400000000)


@transaction.atomic
def submit_request(
    *,
    actor,
    asset_ids,
    site_name,
    site_address,
    responsible,
    starts_at,
    ends_at,
    notes,
    submit_key,
):
    require_customer(actor)
    try:
        key = uuid.UUID(str(submit_key))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("La confirmación no es válida. Actualiza tu selección.")
    if (
        not asset_ids
        or len(asset_ids) > 20
        or any(type(i) is not int or i <= 0 for i in asset_ids)
        or len(set(asset_ids)) != len(asset_ids)
    ):
        raise ValidationError("Selecciona entre 1 y 20 herramientas distintas.")
    if (
        not starts_at
        or not ends_at
        or timezone.is_naive(starts_at)
        or timezone.is_naive(ends_at)
    ):
        raise ValidationError("Indica fechas y horas válidas.")
    payload = {
        "actor": actor.pk,
        "assets": sorted(asset_ids),
        "site": site_name.strip(),
        "address": site_address.strip(),
        "responsible": responsible.strip(),
        "start": starts_at.astimezone(datetime_timezone.utc).isoformat(),
        "end": ends_at.astimezone(datetime_timezone.utc).isoformat(),
        "notes": notes.strip(),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    contractor = Contractor.objects.select_for_update().get(pk=actor.contractor_id)
    previous = (
        RentalRequest.objects.select_for_update()
        .filter(requested_by=actor, submit_key=key)
        .first()
    )
    if previous:
        if previous.fingerprint != digest:
            raise ValidationError(
                "Esta confirmación ya se usó con otros datos. Actualiza la selección."
            )
        return previous
    if starts_at < timezone.now() or ends_at <= starts_at:
        raise ValidationError(
            "El inicio debe ser futuro y la devolución posterior al inicio."
        )
    if not contractor.active or contractor.manual_block or is_delinquent(contractor.pk):
        raise ValidationError(
            "Tu cuenta tiene entregas bloqueadas. Regulariza las devoluciones o contacta a BuildCorp."
        )
    assets = list(
        Asset.objects.select_for_update().filter(pk__in=asset_ids).order_by("pk")
    )
    if len(assets) != len(asset_ids) or any(
        not available_for_request(a) for a in assets
    ):
        raise ValidationError(
            "Alguna herramienta ya no está disponible o requiere revisión. Actualiza la selección."
        )
    estimate = sum(a.daily_rate for a in assets) * _days(starts_at, ends_at)
    req = RentalRequest(
        requested_by=actor,
        contractor=contractor,
        site_name=payload["site"],
        site_address=payload["address"],
        responsible=payload["responsible"],
        starts_at=starts_at,
        ends_at=ends_at,
        notes=payload["notes"],
        estimated_amount=estimate,
        submit_key=key,
        fingerprint=digest,
    )
    req.full_clean()
    req.save()
    RentalRequestItem.objects.bulk_create(
        [
            RentalRequestItem(request=req, asset=a, estimated_daily_rate=a.daily_rate)
            for a in assets
        ]
    )
    return req


@transaction.atomic
def cancel_request(*, request_id, actor):
    require_customer(actor)
    req = RentalRequest.objects.select_for_update().get(pk=request_id)
    if req.contractor_id != actor.contractor_id:
        raise PermissionDenied("La solicitud no pertenece a tu cuenta.")
    _pending(req)
    req.status = "CANCELADA"
    req.resolved_by = actor
    req.resolved_at = timezone.now()
    req.resolution_reason = "Cancelada por el cliente"
    req.save()
    return req


@transaction.atomic
def reject_request(*, request_id, reason, actor):
    require_operator(actor)
    req = RentalRequest.objects.select_for_update().get(pk=request_id)
    _pending(req)
    if not reason.strip():
        raise ValidationError("Indica el motivo del rechazo.")
    req.status = "RECHAZADA"
    req.resolution_reason = reason.strip()
    req.resolved_at = timezone.now()
    req.resolved_by = actor
    req.save()
    return req


def delivery_quote(req, actor):
    rates = [
        [line.asset_id, line.asset.daily_rate]
        for line in req.items.select_related("asset").order_by("asset_id")
    ]
    return signing.dumps(
        {"request": req.pk, "actor": actor.pk, "rates": rates},
        salt="request-delivery",
        compress=True,
    )


@transaction.atomic
def fulfill_request(
    *, request_id, site_id, responsible, due_at, signature, actor, quote=None
):
    require_operator(actor)
    contractor_id = RentalRequest.objects.values_list("contractor_id", flat=True).get(
        pk=request_id
    )
    Contractor.objects.select_for_update().get(pk=contractor_id)
    req = RentalRequest.objects.select_for_update().get(pk=request_id)
    if req.status == "ENTREGADA" and req.loan_id:
        return req.loan
    _pending(req)
    if req.ends_at <= timezone.now():
        raise ValidationError(
            "El plazo de la solicitud venció. Solicita al cliente que envíe nuevas fechas."
        )
    ids = list(req.items.values_list("asset_id", flat=True))
    assets = list(Asset.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    if quote is not None:
        try:
            accepted = signing.loads(quote, salt="request-delivery", max_age=1800)
        except signing.BadSignature as exc:
            raise ValidationError(
                "El resumen venció. Revisa las tarifas y vuelve a firmar."
            ) from exc
        if accepted != {
            "request": req.pk,
            "actor": actor.pk,
            "rates": [[a.pk, a.daily_rate] for a in assets],
        }:
            raise ValidationError(
                "Las tarifas cambiaron. Revisa los nuevos valores y vuelve a firmar."
            )
    loan = issue_loan(
        contractor_id=req.contractor_id,
        site_id=site_id,
        asset_ids=ids,
        due_at=due_at,
        responsible=responsible,
        signature=signature,
        actor=actor,
    )
    req.loan = loan
    req.status = "ENTREGADA"
    req.resolved_by = actor
    req.resolved_at = timezone.now()
    req.resolution_reason = "Entrega firmada registrada"
    req.save()
    return loan
