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
    delivery_quote,
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
        {"base_template": _base(request.user), "rental_request": req},
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
    form = FulfillRequestForm(
        request.POST or None,
        initial={
            "responsible": req.responsible,
            "due_at": req.ends_at,
            "quote": delivery_quote(req, request.user),
        },
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()
        site_id = data.pop("site").pk
        try:
            loan = fulfill_request(
                request_id=pk, site_id=site_id, actor=request.user, **data
            )
            messages.success(request, "Solicitud entregada con firma.")
            return redirect(f"/rentals/{loan.pk}/")
        except ValidationError as exc:
            error(form, exc)
            new_data = form.data.copy()
            new_data["quote"] = delivery_quote(req, request.user)
            form.data = new_data
    lines = [
        {
            "name": line.asset.name,
            "estimated": line.estimated_daily_rate,
            "current": line.asset.daily_rate,
        }
        for line in req.items.select_related("asset")
    ]
    return render(
        request,
        "requests/fulfill.html",
        {
            "form": form,
            "title": f"Confirmar entrega de solicitud #{pk}",
            "back": f"/mis-solicitudes/{pk}/",
            "sign": True,
            "rental_request": req,
            "lines": lines,
        },
    )
