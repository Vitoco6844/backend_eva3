from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.permissions import require_operator
from inventory.models import Asset
from inventory.services import record_event
from .models import MaintenancePlan, MaintenanceJob


def is_due(asset, at=None):
    at = at or timezone.now()
    plan = MaintenancePlan.objects.filter(asset=asset).first()
    return bool(
        plan
        and (
            (plan.due_at is not None and plan.due_at <= at)
            or (plan.due_hours is not None and asset.usage_hours >= plan.due_hours)
        )
    )


def requires_maintenance(asset, damaged=False, at=None):
    return damaged or is_due(asset, at)


@transaction.atomic
def save_plan(*, asset_id, due_at, due_hours, actor):
    require_operator(actor)
    asset = Asset.objects.select_for_update().get(pk=asset_id)
    if due_at is None and due_hours is None:
        raise ValidationError("Indica fecha u horas para la próxima revisión.")
    if due_hours is not None and (
        not Decimal(str(due_hours)).is_finite() or Decimal(str(due_hours)) < 0
    ):
        raise ValidationError("Horas inválidas.")
    plan, _ = MaintenancePlan.objects.update_or_create(
        asset=asset, defaults={"due_at": due_at, "due_hours": due_hours}
    )
    return plan


@transaction.atomic
def start_maintenance(*, asset_id, actor, notes):
    require_operator(actor)
    asset = Asset.objects.select_for_update().get(pk=asset_id)
    if asset.status not in ("DISPONIBLE", "MANTENIMIENTO") or not notes.strip():
        raise ValidationError(
            "El activo debe estar disponible o pendiente de mantenimiento; indica el trabajo."
        )
    if MaintenanceJob.objects.filter(asset=asset, finished_at=None).exists():
        raise ValidationError("Ya tiene un mantenimiento abierto.")
    old = asset.status
    asset.status = "MANTENIMIENTO"
    asset.save(update_fields=["status"])
    job = MaintenanceJob.objects.create(asset=asset, actor=actor, notes=notes)
    record_event(asset, actor, old, "MANTENIMIENTO_INICIO", notes)
    return job


@transaction.atomic
def finish_maintenance(*, job_id, actor, notes, next_due_at, next_due_hours):
    require_operator(actor)
    asset_id = MaintenanceJob.objects.values_list("asset_id", flat=True).get(pk=job_id)
    asset = Asset.objects.select_for_update().get(pk=asset_id)
    job = MaintenanceJob.objects.select_for_update().get(pk=job_id)
    if job.finished_at or asset.status != "MANTENIMIENTO" or not notes.strip():
        raise ValidationError("Mantenimiento ya finalizado o datos inválidos.")
    if next_due_at is None and next_due_hours is None:
        raise ValidationError("Programa la próxima revisión.")
    if next_due_at is not None and next_due_at <= timezone.now():
        raise ValidationError("La próxima fecha debe estar en el futuro.")
    if next_due_hours is not None and Decimal(str(next_due_hours)) <= asset.usage_hours:
        raise ValidationError("El umbral debe superar las horas acumuladas.")
    save_plan(
        asset_id=asset.pk, due_at=next_due_at, due_hours=next_due_hours, actor=actor
    )
    job.finished_at = timezone.now()
    job.finished_by = actor
    job.hours_at_finish = asset.usage_hours
    job.notes += "\nCierre: " + notes
    job.save()
    old = asset.status
    asset.status = "DISPONIBLE"
    asset.save(update_fields=["status"])
    record_event(asset, actor, old, "MANTENIMIENTO_FIN", notes)
    return job
