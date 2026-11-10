from django.db import transaction
from django.core.exceptions import ValidationError
from accounts.permissions import require_operator
from .models import Asset, AssetEvent, Warehouse


def record_event(asset, actor, previous, kind, reason, origin=None):
    return AssetEvent.objects.create(
        asset=asset,
        actor=actor,
        previous_status=previous,
        new_status=asset.status,
        kind=kind,
        reason=reason,
        origin=origin or asset.warehouse,
        destination=asset.warehouse,
    )


@transaction.atomic
def transfer_asset(*, asset_id, warehouse_id, actor, reason):
    require_operator(actor)
    asset = Asset.objects.select_for_update().get(pk=asset_id)
    require_unheld(asset)
    target = Warehouse.objects.select_related("site").get(pk=warehouse_id)
    if asset.status != "DISPONIBLE" or not target.active or not target.site.active:
        raise ValidationError(
            "Solo se trasladan herramientas disponibles a bodegas activas."
        )
    if not reason.strip() or target.pk == asset.warehouse_id:
        raise ValidationError("Indica una bodega distinta y un motivo.")
    origin = asset.warehouse
    asset.warehouse = target
    asset.save(update_fields=["warehouse"])
    record_event(asset, actor, asset.status, "TRASLADO", reason, origin)
    return asset


@transaction.atomic
def retire_asset(*, asset_id, actor, reason):
    require_operator(actor)
    asset = Asset.objects.select_for_update().get(pk=asset_id)
    require_unheld(asset)
    if asset.status != "DISPONIBLE" or not reason.strip():
        raise ValidationError("La baja requiere herramienta disponible y motivo.")
    old = asset.status
    asset.status = "BAJA"
    asset.save(update_fields=["status"])
    record_event(asset, actor, old, "BAJA", reason)
    return asset


def require_unheld(asset):
    from rentals.models import AssetHold

    if AssetHold.objects.filter(asset_id=asset.pk).exists():
        raise ValidationError(
            "La herramienta está retenida para una solicitud aprobada."
        )
