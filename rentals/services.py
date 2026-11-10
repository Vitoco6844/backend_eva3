from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.permissions import require_operator
from inventory.models import Asset, Contractor, Site
from inventory.services import record_event
from maintenance.services import is_due, requires_maintenance
from .models import Loan, LoanItem, Signature, OverdueAlert
from .signatures import validate_signature


def is_delinquent(contractor_id, at=None):
    return Loan.objects.filter(
        contractor_id=contractor_id,
        due_at__lt=at or timezone.now(),
        items__returned_at__isnull=True,
    ).exists()


@transaction.atomic
def refresh_overdue_alerts(at=None):
    at = at or timezone.now()
    count = 0
    for loan in Loan.objects.filter(due_at__lt=at, closed_at=None).order_by("pk"):
        locked = Loan.objects.select_for_update().get(pk=loan.pk)
        if locked.items.filter(returned_at=None).exists():
            _, created = OverdueAlert.objects.get_or_create(
                loan=locked, resolved_at=None
            )
            count += created
    OverdueAlert.objects.filter(resolved_at=None, loan__closed_at__isnull=False).update(
        resolved_at=at
    )
    return count


@transaction.atomic
def issue_loan(
    *, contractor_id, site_id, asset_ids, due_at, responsible, signature, actor
):
    require_operator(actor)
    raw, digest = validate_signature(signature)
    contractor = Contractor.objects.select_for_update().get(pk=contractor_id)
    site = Site.objects.get(pk=site_id)
    now = timezone.now()
    if (
        not contractor.active
        or contractor.manual_block
        or is_delinquent(contractor.pk, now)
    ):
        raise ValidationError(
            "Contratista inactivo, bloqueado o con devoluciones vencidas."
        )
    if not site.active or not responsible.strip() or not due_at or due_at <= now:
        raise ValidationError("Obra, responsable o vencimiento inválidos.")
    if not asset_ids or len(set(asset_ids)) != len(asset_ids):
        raise ValidationError("Selecciona herramientas distintas.")
    assets = list(
        Asset.objects.select_for_update().filter(pk__in=asset_ids).order_by("pk")
    )
    if len(assets) != len(asset_ids):
        raise ValidationError("Una herramienta no existe.")
    for asset in assets:
        if (
            asset.status != "DISPONIBLE"
            or is_due(asset, now)
            or not asset.category.active
            or not asset.warehouse.active
            or not asset.warehouse.site.active
        ):
            raise ValidationError(
                f"{asset.code}: no está disponible o requiere revisión."
            )
        if LoanItem.objects.filter(asset=asset, returned_at=None).exists():
            raise ValidationError("Herramienta ya prestada.")
    loan = Loan.objects.create(
        contractor=contractor,
        site=site,
        responsible=responsible,
        issued_at=now,
        due_at=due_at,
        actor=actor,
    )
    Signature.objects.create(
        loan=loan,
        kind="ENTREGA",
        name=responsible,
        actor=actor,
        image=raw,
        digest=digest,
    )
    for asset in assets:
        LoanItem.objects.create(loan=loan, asset=asset, daily_rate=asset.daily_rate)
        old = asset.status
        asset.status = "EN_USO"
        asset.save(update_fields=["status"])
        record_event(asset, actor, old, "ENTREGA", f"Préstamo #{loan.pk}")
    return loan


@transaction.atomic
def return_items(*, loan_id, items, signature, actor):
    require_operator(actor)
    raw, digest = validate_signature(signature)
    contractor_id = Loan.objects.values_list("contractor_id", flat=True).get(pk=loan_id)
    Contractor.objects.select_for_update().get(pk=contractor_id)
    loan = Loan.objects.select_for_update().get(pk=loan_id)
    if loan.closed_at or not items:
        raise ValidationError("Préstamo cerrado o devolución vacía.")
    ids = [i["item_id"] for i in items]
    if len(ids) != len(set(ids)):
        raise ValidationError("No repitas herramientas.")
    lines = {line.pk: line for line in loan.items.filter(pk__in=ids)}
    if len(lines) != len(ids) or any(line.returned_at for line in lines.values()):
        raise ValidationError("Línea ajena o ya devuelta.")
    assets = {
        a.pk: a
        for a in Asset.objects.select_for_update()
        .filter(pk__in=[line.asset_id for line in lines.values()])
        .order_by("pk")
    }
    parsed = []
    for data in items:
        try:
            hours = Decimal(str(data.get("usage_hours", "0")))
            if (
                not hours.is_finite()
                or hours < 0
                or hours > Decimal("9999999999.99")
                or hours != hours.quantize(Decimal(".01"))
            ):
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise ValidationError(
                "Las horas deben ser positivas o cero, con máximo dos decimales."
            )
        if not isinstance(data.get("damaged", False), bool):
            raise ValidationError("Condición de daño inválida.")
        line = lines[data["item_id"]]
        asset = assets[line.asset_id]
        if asset.status != "EN_USO" or asset.usage_hours + hours > Decimal(
            "9999999999.99"
        ):
            raise ValidationError("Estado u horas acumuladas inválidos.")
        parsed.append((line, asset, hours, data))
    sig = Signature.objects.create(
        loan=loan,
        kind="DEVOLUCION",
        name=loan.responsible,
        actor=actor,
        image=raw,
        digest=digest,
    )
    now = timezone.now()
    for line, asset, hours, data in parsed:
        line.returned_at = now
        line.usage_hours = hours
        line.damaged = data.get("damaged", False)
        line.notes = data.get("notes", "")
        line.return_signature = sig
        line.save()
        asset.usage_hours += hours
        old = asset.status
        asset.status = (
            "MANTENIMIENTO"
            if requires_maintenance(asset, line.damaged, now)
            else "DISPONIBLE"
        )
        asset.save(update_fields=["status", "usage_hours"])
        record_event(
            asset, actor, old, "DEVOLUCION", f"Préstamo #{loan.pk}. {line.notes}"
        )
    if not loan.items.filter(returned_at=None).exists():
        loan.closed_at = now
        loan.save(update_fields=["closed_at"])
        from payments.services import close_charge

        close_charge(loan)
        OverdueAlert.objects.filter(loan=loan, resolved_at=None).update(resolved_at=now)
    return loan
