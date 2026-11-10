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
def _submit_request(
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
    contractor_id=None,
):
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
    contractor = Contractor.objects.select_for_update().get(
        pk=contractor_id or actor.contractor_id
    )
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


def submit_request(**kwargs):
    require_customer(kwargs["actor"])
    return _submit_request(**kwargs)


def cancel_request(*, request_id, actor):
    from .approval_services import resolve_unpaid

    return resolve_unpaid(
        request_id=request_id,
        actor=actor,
        status="CANCELADA",
        reason="Cancelada por el cliente",
    )


def reject_request(*, request_id, reason, actor):
    from .approval_services import resolve_unpaid

    return resolve_unpaid(
        request_id=request_id, actor=actor, status="RECHAZADA", reason=reason
    )


@transaction.atomic
def fulfill_request(
    *, request_id, signature, responsible, actor, site_id=None, due_at=None, quote=None
):
    require_operator(actor)
    from .approval_services import locked_request
    from payments.models import Charge
    from .models import AssetHold

    contractor, req = locked_request(request_id)
    if req.status == "ENTREGADA" and req.loan_id:
        return req.loan
    if req.status != "PAGADA":
        raise ValidationError(
            "Debes aprobar la solicitud y confirmar su pago antes de entregar."
        )
    charge = Charge.objects.select_for_update().get(rental_request=req, kind="INITIAL")
    if not charge.paid_at or charge.voided_at or charge.amount != req.approved_amount:
        raise ValidationError(
            "El pago inicial no está confirmado o no coincide con la aprobación."
        )
    if (site_id is not None and site_id != req.approved_site_id) or (
        due_at is not None and due_at != req.ends_at
    ):
        raise ValidationError(
            "Las fechas y la obra aprobadas no pueden cambiar después del pago."
        )
    now = timezone.now()
    if now < req.starts_at or now >= req.ends_at:
        raise ValidationError(
            "Entrega fuera del período aprobado. Contacta a BuildCorp para revisar el caso."
        )
    lines = list(req.items.order_by("asset_id"))
    ids = [line.asset_id for line in lines]
    assets = list(Asset.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    held = set(AssetHold.objects.filter(request=req).values_list("asset_id", flat=True))
    if held != set(ids) or not ids:
        raise ValidationError(
            "La retención de herramientas requiere revisión. No se modificó el pago."
        )
    from .services import _issue_approved_loan

    loan = _issue_approved_loan(
        contractor_id=req.contractor_id,
        site_id=req.approved_site_id,
        asset_ids=ids,
        due_at=req.ends_at,
        responsible=responsible,
        signature=signature,
        actor=actor,
        request_id=req.pk,
    )
    for line in loan.items.all():
        line.daily_rate = next(
            item.approved_daily_rate for item in lines if item.asset_id == line.asset_id
        )
        line.save(update_fields=["daily_rate"])
    charge.loan = loan
    charge.save(update_fields=["loan"])
    req.holds.all().delete()
    req.loan = loan
    req.status = "ENTREGADA"
    req.resolved_by = actor
    req.resolved_at = now
    req.resolution_reason = "Entrega firmada con pago previo confirmado"
    req.save()
    return loan
