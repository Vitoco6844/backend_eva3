from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from accounts.permissions import can_operate, require_operator, contractor_scope
from inventory.models import Contractor, Site, Warehouse, Category, Asset
from inventory.services import transfer_asset, retire_asset, record_event
from rentals.models import Loan, Signature
from rentals.services import (
    issue_loan,
    return_items,
    is_delinquent,
    refresh_overdue_alerts,
)
from maintenance.models import MaintenancePlan, MaintenanceJob
from maintenance.services import (
    is_due,
    start_maintenance,
    finish_maintenance,
    save_plan,
)
from payments.services import visible_charges, start_payment, reconcile_payment
from .forms import (
    IssueForm,
    ReturnForm,
    StartForm,
    FinishForm,
    PlanForm,
    TransferForm,
    ReasonForm,
)

MASTERS = {
    "assets": (
        Asset,
        "Herramientas",
        [
            "code",
            "name",
            "serial",
            "image",
            "category",
            "warehouse",
            "description",
            "daily_rate",
        ],
    ),
    "contractors": (
        Contractor,
        "Contratistas",
        ["name", "tax_id", "email", "phone", "active", "manual_block"],
    ),
    "sites": (Site, "Obras", ["name", "address", "active"]),
    "warehouses": (Warehouse, "Bodegas", ["name", "site", "active"]),
    "categories": (Category, "Categorías", ["name", "active"]),
}


def context(request, **kwargs):
    return {"operator": can_operate(request.user), **kwargs}


def error(form, exc):
    form.add_error(
        None,
        " ".join(exc.messages)
        if isinstance(exc, ValidationError)
        else "Operación incompatible con registros relacionados o una operación simultánea.",
    )


def form_page(request, form, title, back, sign=False):
    return render(
        request,
        "form.html",
        context(request, form=form, title=title, back=back, sign=sign),
    )


@login_required
def dashboard(request):
    loans = contractor_scope(
        request.user, Loan.objects.select_related("contractor", "site")
    )
    charges = visible_charges(request.user)
    ctx = {
        "loans": loans.filter(closed_at=None)[:6],
        "open_count": loans.filter(closed_at=None).count(),
        "overdue_count": loans.filter(
            due_at__lt=timezone.now(), closed_at=None
        ).count(),
        "pending_count": charges.filter(paid_at=None).count(),
    }
    if can_operate(request.user):
        ctx.update(
            available=Asset.objects.filter(status="DISPONIBLE").count(),
            due_assets=[a for a in Asset.objects.exclude(status="BAJA") if is_due(a)][
                :6
            ],
        )
    return render(request, "dashboard.html", context(request, **ctx))


@login_required
def master_list(request, kind):
    require_operator(request.user)
    if kind not in MASTERS:
        raise PermissionDenied()
    model, title, fields = MASTERS[kind]
    qs = model.objects.all()
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        qs = (
            qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
            if kind == "assets"
            else qs.filter(name__icontains=q)
        )
    if kind == "assets":
        qs = qs.select_related("category", "warehouse")
        if status:
            qs = qs.filter(status=status)
    return render(
        request,
        "inventory/list.html",
        context(
            request,
            title=title,
            kind=kind,
            page=Paginator(qs, 20).get_page(request.GET.get("page")),
            q=q,
            status=status,
            statuses=Asset.Status.choices,
        ),
    )


@login_required
def master_form(request, kind, pk=None):
    require_operator(request.user)
    if kind not in MASTERS:
        raise PermissionDenied()
    if (
        kind == "contractors"
        and request.user.role != "ADMIN"
        and not request.user.is_superuser
    ):
        raise PermissionDenied("Solo administración gestiona contratistas.")
    model, title, fields = MASTERS[kind]
    obj = get_object_or_404(model, pk=pk) if pk else None
    Form = modelform_factory(
        model,
        fields=[
            f for f in fields if not (obj and kind == "assets" and f == "warehouse")
        ],
    )
    form = Form(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                if obj:
                    locked = model.objects.select_for_update().get(pk=pk)
                    for field in form.changed_data:
                        setattr(locked, field, form.cleaned_data[field])
                    locked.full_clean()
                    locked.save(update_fields=form.changed_data)
                else:
                    locked = form.save()
                    if kind == "assets":
                        record_event(
                            locked, request.user, "", "ALTA", "Alta en catálogo"
                        )
            messages.success(request, "Datos guardados.")
            return redirect(f"/inventory/{kind}/")
        except (ValidationError, IntegrityError) as exc:
            error(form, exc)
    return form_page(
        request,
        form,
        ("Editar " if obj else "Crear ") + title.lower(),
        f"/inventory/{kind}/",
    )


@login_required
def master_delete(request, kind, pk):
    require_operator(request.user)
    if kind not in MASTERS:
        raise PermissionDenied()
    if not request.user.is_superuser and request.user.role != "ADMIN":
        raise PermissionDenied("Solo administración elimina registros sin historial.")
    obj = get_object_or_404(MASTERS[kind][0], pk=pk)
    if request.method == "POST":
        try:
            with transaction.atomic():
                obj.delete()
            messages.success(request, "Registro eliminado.")
        except ProtectedError:
            messages.error(
                request,
                "Este registro tiene historial. Consérvalo y usa desactivación o baja.",
            )
        return redirect(f"/inventory/{kind}/")
    return render(
        request,
        "confirm.html",
        context(
            request, title="Eliminar registro", obj=obj, back=f"/inventory/{kind}/"
        ),
    )


@login_required
def asset_detail(request, pk):
    require_operator(request.user)
    asset = get_object_or_404(
        Asset.objects.select_related("category", "warehouse__site"), pk=pk
    )
    return render(
        request,
        "inventory/detail.html",
        context(
            request,
            asset=asset,
            events=asset.events.select_related("actor", "origin", "destination"),
            due=is_due(asset),
        ),
    )


@login_required
def asset_action(request, pk, action):
    require_operator(request.user)
    asset = get_object_or_404(Asset, pk=pk)
    if action not in ("transfer", "retire"):
        raise PermissionDenied()
    form = (TransferForm if action == "transfer" else ReasonForm)(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            if action == "transfer":
                transfer_asset(
                    asset_id=pk,
                    warehouse_id=form.cleaned_data["warehouse"].pk,
                    actor=request.user,
                    reason=form.cleaned_data["reason"],
                )
            else:
                retire_asset(
                    asset_id=pk, actor=request.user, reason=form.cleaned_data["reason"]
                )
            messages.success(request, "Operación registrada en el historial.")
            return redirect(f"/inventory/assets/{pk}/")
        except ValidationError as exc:
            error(form, exc)
    return form_page(
        request,
        form,
        ("Trasladar " if action == "transfer" else "Dar de baja ") + asset.name,
        f"/inventory/assets/{pk}/",
    )


@login_required
def loans(request):
    qs = contractor_scope(
        request.user, Loan.objects.select_related("contractor", "site")
    )
    return render(
        request,
        "rentals/list.html",
        context(request, page=Paginator(qs, 20).get_page(request.GET.get("page"))),
    )


@login_required
def issue(request):
    require_operator(request.user)
    form = IssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            loan = issue_loan(
                contractor_id=d["contractor"].pk,
                site_id=d["site"].pk,
                asset_ids=list(d["assets"].values_list("pk", flat=True)),
                due_at=d["due_at"],
                responsible=d["responsible"],
                signature=d["signature"],
                actor=request.user,
            )
            messages.success(request, "Entrega registrada y firmada.")
            return redirect(f"/rentals/{loan.pk}/")
        except (ValidationError, IntegrityError) as exc:
            error(form, exc)
    return form_page(request, form, "Entregar herramientas", "/rentals/", True)


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(
        contractor_scope(
            request.user,
            Loan.objects.select_related("contractor", "site").prefetch_related(
                "items__asset", "signatures"
            ),
        ),
        pk=pk,
    )
    return render(
        request,
        "rentals/detail.html",
        context(
            request,
            loan=loan,
            overdue=loan.closed_at is None and loan.due_at < timezone.now(),
        ),
    )


@login_required
def return_loan(request, pk):
    require_operator(request.user)
    loan = get_object_or_404(Loan, pk=pk)
    form = ReturnForm(request.POST or None, loan=loan)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        items = []
        for line in loan.items.filter(returned_at=None):
            if data.get(f"select_{line.pk}"):
                hours = data.get(f"hours_{line.pk}")
                if hours is None:
                    form.add_error(f"hours_{line.pk}", "Indica las horas utilizadas.")
                    continue
                items.append(
                    {
                        "item_id": line.pk,
                        "usage_hours": hours,
                        "damaged": data[f"damaged_{line.pk}"],
                        "notes": data[f"notes_{line.pk}"],
                    }
                )
        if not form.errors:
            try:
                return_items(
                    loan_id=pk,
                    items=items,
                    signature=data["signature"],
                    actor=request.user,
                )
                messages.success(request, "Devolución registrada.")
                return redirect(f"/rentals/{pk}/")
            except (ValidationError, IntegrityError) as exc:
                error(form, exc)
    return form_page(
        request,
        form,
        f"Devolver herramientas del préstamo #{pk}",
        f"/rentals/{pk}/",
        True,
    )


@login_required
def signature_image(request, pk):
    sig = get_object_or_404(
        Signature.objects.filter(
            loan__in=contractor_scope(request.user, Loan.objects.all())
        ),
        pk=pk,
    )
    response = HttpResponse(bytes(sig.image), content_type="image/png")
    response["Cache-Control"] = "private, no-store"
    response["Content-Disposition"] = 'inline; filename="firma.png"'
    return response


@login_required
def maintenance(request):
    require_operator(request.user)
    return render(
        request,
        "maintenance/list.html",
        context(
            request,
            plans=MaintenancePlan.objects.select_related("asset"),
            jobs=MaintenanceJob.objects.select_related("asset", "actor").order_by(
                "-pk"
            ),
            due_assets=[a for a in Asset.objects.exclude(status="BAJA") if is_due(a)],
        ),
    )


@login_required
def maintenance_form(request, action, pk=None):
    require_operator(request.user)
    if action not in ("plan", "start", "finish"):
        raise PermissionDenied()
    obj = get_object_or_404(MaintenancePlan, pk=pk) if pk and action == "plan" else None
    form = (
        PlanForm(request.POST or None, instance=obj)
        if action == "plan"
        else (StartForm if action == "start" else FinishForm)(request.POST or None)
    )
    if action == "finish":
        get_object_or_404(MaintenanceJob, pk=pk)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            if action == "plan":
                if obj and d["asset"].pk != obj.asset_id:
                    raise ValidationError(
                        "No se cambia el activo de un plan existente."
                    )
                save_plan(
                    asset_id=d["asset"].pk,
                    due_at=d["due_at"],
                    due_hours=d["due_hours"],
                    actor=request.user,
                )
            elif action == "start":
                start_maintenance(
                    asset_id=d["asset"].pk, notes=d["notes"], actor=request.user
                )
            else:
                finish_maintenance(job_id=pk, actor=request.user, **d)
            messages.success(request, "Mantenimiento actualizado.")
            return redirect("/maintenance/")
        except (ValidationError, IntegrityError) as exc:
            error(form, exc)
    return form_page(
        request,
        form,
        {
            "plan": "Programar revisión preventiva",
            "start": "Iniciar mantenimiento",
            "finish": "Finalizar mantenimiento",
        }[action],
        "/maintenance/",
    )


@login_required
def alerts(request):
    require_operator(request.user)
    if request.method == "POST":
        refresh_overdue_alerts()
        messages.success(request, "Alertas revisadas.")
        return redirect("/alerts/")
    overdue = Loan.objects.filter(
        due_at__lt=timezone.now(), closed_at=None
    ).select_related("contractor", "site")
    return render(
        request,
        "alerts.html",
        context(
            request,
            overdue=overdue,
            blocked=[
                c
                for c in Contractor.objects.all()
                if c.manual_block or is_delinquent(c.pk)
            ],
        ),
    )


@login_required
def charges(request):
    return render(
        request,
        "payments/list.html",
        context(request, charges=visible_charges(request.user).order_by("-pk")),
    )


@login_required
def charge_detail(request, pk):
    charge = get_object_or_404(visible_charges(request.user), pk=pk)
    if request.method == "POST":
        try:
            if request.POST.get("action") == "reconcile":
                attempt = charge.attempts.order_by("-pk").first()
                if attempt:
                    reconcile_payment(attempt.pk)
                    messages.info(request, "Estado consultado con Transbank.")
            else:
                attempt = start_payment(charge_id=pk, actor=request.user)
                if attempt.status == "PENDING":
                    return redirect(f"/payments/{pk}/continue/")
                messages.error(
                    request,
                    "No se confirmó la creación. El intento quedó por conciliar para evitar duplicados.",
                )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect(f"/payments/{pk}/")
    return render(
        request,
        "payments/detail.html",
        context(
            request,
            charge=charge,
            attempts=charge.attempts.order_by("-pk"),
            active_attempt=charge.attempts.filter(
                status__in=("CREATING", "PENDING", "UNKNOWN")
            ).first(),
        ),
    )


@login_required
def payment_continue(request, pk):
    charge = get_object_or_404(visible_charges(request.user), pk=pk)
    if request.user.contractor_id != charge.loan.contractor_id:
        raise PermissionDenied()
    attempt = get_object_or_404(charge.attempts, status="PENDING")
    response = render(
        request, "payments/redirect.html", context(request, attempt=attempt)
    )
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response
