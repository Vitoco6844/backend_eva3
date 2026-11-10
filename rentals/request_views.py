from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from accounts.permissions import require_operator, can_operate
from web.views import form_page, error
from .models import RentalRequest
from .request_services import (
    visible_requests,
    require_customer,
    cancel_request,
    reject_request,
    fulfill_request,
)
from .request_forms import FulfillRequestForm, RejectRequestForm


def _base(user):
    return "base.html" if can_operate(user) else "public/base.html"


@login_required
def mine(request):
    if can_operate(request.user):
        return redirect("/solicitudes/")
    require_customer(request.user)
    return render(
        request,
        "requests/list.html",
        {
            "base_template": _base(request.user),
            "page": Paginator(visible_requests(request.user), 15).get_page(
                request.GET.get("page")
            ),
        },
    )


@login_required
def inbox(request):
    require_operator(request.user)
    qs = visible_requests(request.user)
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    return render(
        request,
        "requests/list.html",
        {
            "base_template": "base.html",
            "page": Paginator(qs, 20).get_page(request.GET.get("page")),
            "statuses": RentalRequest.Status.choices,
            "status": status,
        },
    )


@login_required
def detail(request, pk):
    req = get_object_or_404(visible_requests(request.user), pk=pk)
    return render(
        request,
        "requests/detail.html",
        {
            "base_template": _base(request.user),
            "rental_request": req,
            "initial_charge": req.charges.filter(kind="INITIAL").first(),
        },
    )


@login_required
@require_POST
def cancel(request, pk):
    req = get_object_or_404(visible_requests(request.user), pk=pk)
    try:
        cancel_request(request_id=req.pk, actor=request.user)
        messages.success(request, "Solicitud cancelada.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect(f"/mis-solicitudes/{pk}/")


@login_required
def reject(request, pk):
    require_operator(request.user)
    req = get_object_or_404(visible_requests(request.user), pk=pk)
    form = RejectRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reject_request(request_id=pk, actor=request.user, **form.cleaned_data)
            messages.success(request, "Solicitud rechazada con motivo.")
            return redirect(f"/mis-solicitudes/{pk}/")
        except ValidationError as exc:
            error(form, exc)
    return form_page(
        request, form, f"Rechazar solicitud #{pk}", f"/mis-solicitudes/{pk}/"
    )


@login_required
def fulfill(request, pk):
    require_operator(request.user)
    req = get_object_or_404(visible_requests(request.user), pk=pk)
    if req.loan_id:
        return redirect(f"/rentals/{req.loan_id}/")
    if req.status != "PAGADA":
        messages.error(
            request,
            "Primero aprueba la solicitud y espera el pago confirmado del cliente.",
        )
        return redirect(f"/mis-solicitudes/{pk}/")
    form = FulfillRequestForm(
        request.POST or None, initial={"responsible": req.responsible}
    )
    if request.method == "POST" and form.is_valid():
        try:
            loan = fulfill_request(
                request_id=pk, actor=request.user, **form.cleaned_data
            )
            messages.success(request, "Entrega firmada con pago previo confirmado.")
            return redirect(f"/rentals/{loan.pk}/")
        except ValidationError as exc:
            error(form, exc)
    return render(
        request,
        "requests/fulfill.html",
        {
            "form": form,
            "title": f"Entregar solicitud pagada #{pk}",
            "back": f"/mis-solicitudes/{pk}/",
            "sign": True,
            "rental_request": req,
        },
    )


@login_required
def approve(request, pk):
    from .approval_services import approve_request, approval_quote
    from .request_forms import ApprovalForm

    require_operator(request.user)
    req = get_object_or_404(visible_requests(request.user), pk=pk)
    if req.status != "PENDIENTE":
        return redirect(f"/mis-solicitudes/{pk}/")
    form = ApprovalForm(
        request.POST or None, initial={"quote": approval_quote(req, request.user)}
    )
    if request.method == "POST" and form.is_valid():
        try:
            approve_request(
                request_id=pk,
                site_id=form.cleaned_data["site"].pk,
                quote=form.cleaned_data["quote"],
                actor=request.user,
            )
            messages.success(
                request,
                "Solicitud aprobada y equipos retenidos. El cliente debe pagar antes de entregar.",
            )
            return redirect(f"/mis-solicitudes/{pk}/")
        except ValidationError as exc:
            error(form, exc)
            req.refresh_from_db()
            data = form.data.copy()
            data["quote"] = approval_quote(req, request.user)
            form.data = data
    from .request_services import _days

    lines = list(req.items.select_related("asset"))
    return render(
        request,
        "requests/approve.html",
        {
            "form": form,
            "title": f"Aprobar solicitud #{pk}",
            "back": f"/mis-solicitudes/{pk}/",
            "rental_request": req,
            "lines": lines,
            "amount": sum(l.asset.daily_rate for l in lines)
            * _days(req.starts_at, req.ends_at),
        },
    )


@login_required
def prepare(request):
    import uuid
    from datetime import timedelta
    from django.utils import timezone
    from .request_forms import OperatorRequestForm
    from .approval_services import create_operator_request

    require_operator(request.user)
    now = timezone.localtime(timezone.now()) + timedelta(minutes=2)
    form = OperatorRequestForm(
        request.POST or None,
        initial={
            "submit_key": uuid.uuid4(),
            "starts_at": now.strftime("%Y-%m-%dT%H:%M"),
            "ends_at": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
        },
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()
        data["contractor_id"] = data.pop("contractor").pk
        data["asset_ids"] = [a.pk for a in data.pop("assets")]
        try:
            req = create_operator_request(actor=request.user, **data)
            messages.success(
                request,
                "Solicitud creada. Aprueba la tarifa para que su titular pueda pagar.",
            )
            return redirect(f"/mis-solicitudes/{req.pk}/")
        except ValidationError as exc:
            error(form, exc)
    return form_page(
        request, form, "Preparar solicitud para un contratista", "/solicitudes/"
    )
