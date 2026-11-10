import uuid
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.http import JsonResponse
from rentals.request_services import _days
from inventory.catalog import public_assets, prepare_asset, available_for_request
from rentals.request_forms import RentalRequestForm
from rentals.request_services import submit_request, require_customer


def request_selection(session):
    values = session.get("rental_selection", [])
    return (
        list(dict.fromkeys(v for v in values if type(v) is int and v > 0))[:20]
        if isinstance(values, list)
        else []
    )


def _changed(session):
    session.pop("rental_submit_key", None)
    session.pop("rental_submit_assets", None)


@require_POST
def add(request, pk):
    asset = get_object_or_404(public_assets(), pk=pk)
    ids = request_selection(request.session)
    if not available_for_request(asset):
        messages.error(request, "Esta herramienta no está disponible para solicitarla.")
    elif pk not in ids:
        if len(ids) >= 20:
            messages.error(request, "Tu selección admite hasta 20 herramientas.")
        else:
            ids.append(pk)
            request.session["rental_selection"] = ids
            _changed(request.session)
            messages.success(request, "Herramienta agregada a tu selección.")
    return redirect("/mi-solicitud/")


@require_POST
def remove(request, pk):
    request.session["rental_selection"] = [
        i for i in request_selection(request.session) if i != pk
    ]
    _changed(request.session)
    return redirect("/mi-solicitud/")


@require_POST
def clear(request):
    request.session["rental_selection"] = []
    _changed(request.session)
    return redirect("/mi-solicitud/")


def _render(request, form=None):
    ids = request_selection(request.session)
    assets = [prepare_asset(a) for a in public_assets().filter(pk__in=ids)]
    if form is None:
        if (
            not request.session.get("rental_submit_key")
            or request.session.get("rental_submit_assets") != ids
        ):
            request.session["rental_submit_key"] = str(uuid.uuid4())
            request.session["rental_submit_assets"] = ids
        now = timezone.localtime(timezone.now()) + timedelta(hours=1)
        form = RentalRequestForm(
            initial={
                "submit_key": request.session["rental_submit_key"],
                "starts_at": now.strftime("%Y-%m-%dT%H:%M"),
                "ends_at": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "responsible": request.user.get_full_name()
                if request.user.is_authenticated
                else "",
            }
        )
    estimate = sum(a.daily_rate for a in assets)
    return render(
        request,
        "public/selection.html",
        {
            "assets": assets,
            "missing_count": len(ids) - len(assets),
            "form": form,
            "daily_total": estimate,
        },
    )


def selection(request):
    return _render(request)


@require_POST
def submit(request):
    if not request.user.is_authenticated:
        return redirect("/accounts/login/?next=/mi-solicitud/")
    require_customer(request.user)
    form = RentalRequestForm(request.POST)
    if form.is_valid():
        if str(form.cleaned_data["submit_key"]) != request.session.get(
            "rental_submit_key"
        ):
            form.add_error(
                None, "La selección cambió. Actualiza la página antes de confirmar."
            )
        else:
            try:
                req = submit_request(
                    actor=request.user,
                    asset_ids=request.session.get("rental_submit_assets", []),
                    **form.cleaned_data,
                )
                request.session["rental_selection"] = []
                messages.success(
                    request,
                    "Solicitud enviada. Bodega revisará la entrega; las herramientas aún no están reservadas.",
                )
                return redirect(f"/mis-solicitudes/{req.pk}/")
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
    return _render(request, form)


@require_POST
def estimate(request):
    try:
        start = RentalRequestForm.base_fields["starts_at"].clean(
            request.POST.get("starts_at")
        )
        end = RentalRequestForm.base_fields["ends_at"].clean(
            request.POST.get("ends_at")
        )
        if start < timezone.now() or end <= start:
            raise ValidationError("Revisa las fechas previstas.")
        ids = request_selection(request.session)
        assets = public_assets().filter(pk__in=ids)
        days = _days(start, end)
        amount = sum(a.daily_rate for a in assets) * days
        return JsonResponse({"amount": amount, "days": days})
    except ValidationError as exc:
        return JsonResponse({"detail": " ".join(exc.messages)}, status=400)
