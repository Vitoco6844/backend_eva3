"""Aprobaciones y retenciones de unidades físicas, sin llamadas bancarias."""

from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from accounts.permissions import require_operator
from inventory.models import Contractor, Asset, Site
from inventory.catalog import available_for_request
from inventory.services import record_event
from .models import RentalRequest, AssetHold
from .services import is_delinquent


def locked_request(request_id):
    owner = RentalRequest.objects.values_list("contractor_id", flat=True).get(
        pk=request_id
    )
    contractor = Contractor.objects.select_for_update().get(pk=owner)
    return contractor, RentalRequest.objects.select_for_update().get(pk=request_id)


def quote_data(req, actor, assets=None):
    if assets is None:
        assets = [
            line.asset
            for line in req.items.select_related("asset").order_by("asset_id")
        ]
    return {
        "request": req.pk,
        "actor": actor.pk,
        "start": req.starts_at.isoformat(),
        "end": req.ends_at.isoformat(),
        "rates": [[a.pk, a.daily_rate] for a in assets],
    }


def approval_quote(req, actor):
    require_operator(actor)
    return signing.dumps(quote_data(req, actor), salt="request-approval", compress=True)


@transaction.atomic
def approve_request(*, request_id, site_id, quote, actor):
    require_operator(actor)
    contractor, req = locked_request(request_id)
    if req.status in ("APROBADA", "PAGADA", "ENTREGADA"):
        if req.approved_site_id != site_id:
            raise ValidationError("La aprobación ya está fijada; no cambies la obra.")
        return req
    if req.status != "PENDIENTE" or req.ends_at <= timezone.now():
        raise ValidationError("La solicitud ya fue resuelta o su plazo venció.")
    if not contractor.active or contractor.manual_block or is_delinquent(contractor.pk):
        raise ValidationError("El contratista tiene entregas bloqueadas.")
    site = Site.objects.get(pk=site_id)
    if not site.active:
        raise ValidationError("La obra no está activa.")
    lines = list(req.items.order_by("asset_id"))
    assets = list(
        Asset.objects.select_for_update()
        .filter(pk__in=[l.asset_id for l in lines])
        .order_by("pk")
    )
    try:
        accepted = signing.loads(quote, salt="request-approval", max_age=1800)
    except signing.BadSignature as exc:
        raise ValidationError("El resumen venció; revisa las tarifas.") from exc
    if accepted != quote_data(req, actor, assets):
        raise ValidationError("Las tarifas o fechas cambiaron. Revisa la aprobación.")
    if not assets or any(not available_for_request(a) for a in assets):
        raise ValidationError("Alguna herramienta no está disponible o está retenida.")
    from .request_services import _days
    from payments.models import Charge

    amount = sum(a.daily_rate for a in assets) * _days(req.starts_at, req.ends_at)
    req.approved_at = timezone.now()
    req.approved_by = actor
    req.approved_site = site
    req.approved_amount = amount
    req.status = "APROBADA"
    req.save()
    for line, asset in zip(lines, assets):
        line.approved_daily_rate = asset.daily_rate
        line.save(update_fields=["approved_daily_rate"])
        AssetHold.objects.create(request=req, asset=asset)
        record_event(
            asset, actor, asset.status, "RETENCION", f"Solicitud #{req.pk} aprobada"
        )
    Charge.objects.create(rental_request=req, kind="INITIAL", amount=amount)
    return req


@transaction.atomic
def resolve_unpaid(*, request_id, actor, status, reason):
    contractor, req = locked_request(request_id)
    if status == "CANCELADA":
        from .request_services import require_customer

        require_customer(actor)
        if actor.contractor_id != req.contractor_id:
            raise PermissionDenied("La solicitud no pertenece a tu cuenta.")
    else:
        require_operator(actor)
        if not reason.strip():
            raise ValidationError("Indica el motivo del rechazo.")
    if req.status not in ("PENDIENTE", "APROBADA"):
        raise ValidationError(
            "La solicitud no admite cancelación; si está pagada contacta a BuildCorp."
        )
    from payments.models import Charge

    charges = list(Charge.objects.select_for_update().filter(rental_request=req))
    for charge in charges:
        if (
            charge.paid_at
            or charge.attempts.filter(
                status__in=["CREATING", "PENDING", "UNKNOWN"]
            ).exists()
        ):
            raise ValidationError(
                "Existe un pago activo o por conciliar. Consulta su estado antes de cancelar."
            )
    ids = list(req.holds.values_list("asset_id", flat=True))
    assets = list(Asset.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    for charge in charges:
        charge.voided_at = timezone.now()
        charge.save(update_fields=["voided_at"])
    req.holds.all().delete()
    for asset in assets:
        record_event(
            asset, actor, asset.status, "LIBERACION", f"Solicitud #{req.pk}: {reason}"
        )
    req.status = status
    req.resolved_by = actor
    req.resolved_at = timezone.now()
    req.resolution_reason = reason
    req.save()
    return req


def create_operator_request(*, contractor_id, actor, **kwargs):
    require_operator(actor)
    from .request_services import _submit_request

    return _submit_request(actor=actor, contractor_id=contractor_id, **kwargs)
