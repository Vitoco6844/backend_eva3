from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_safe

from .models import User
from .permissions import can_administer


STAFF_ROLES = (User.Role.ADMIN, User.Role.STORE)


class StaffCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [(role.value, role.label) for role in STAFF_ROLES]
        self.fields["role"].initial = User.Role.STORE


class AccountEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("role", "is_active")
        labels = {"is_active": "Cuenta activa"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.role in STAFF_ROLES:
            self.fields["role"].choices = [
                (role.value, role.label) for role in STAFF_ROLES
            ]
        else:
            del self.fields["role"]


def admin_required(view):
    @login_required
    @wraps(view)
    def protected(request, *args, **kwargs):
        if not can_administer(request.user):
            raise PermissionDenied("Solo administradores pueden gestionar cuentas.")
        return view(request, *args, **kwargs)

    return protected


@admin_required
@require_safe
def index(request):
    return render(request, "administration/index.html")


@admin_required
@require_safe
def users(request):
    q = request.GET.get("q", "").strip()[:150]
    accounts = User.objects.order_by("username", "pk")
    if q:
        accounts = accounts.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    page = Paginator(accounts, 25).get_page(request.GET.get("page"))
    return render(request, "administration/users.html", {"page": page, "q": q})


@admin_required
@require_http_methods(["GET", "POST", "HEAD"])
def create(request):
    form = StaffCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                actor = User.objects.select_for_update().get(pk=request.user.pk)
                if not can_administer(actor):
                    raise PermissionDenied
                form.save()
        except IntegrityError:
            form.add_error(None, "El nombre de usuario o correo ya está en uso.")
        else:
            messages.success(request, "Cuenta de personal creada.")
            return redirect("administration:users")
    return _render_form(request, form, "Crear cuenta de personal")


def _require_editable(actor, account):
    if (
        actor is None
        or not can_administer(actor)
        or account.is_superuser
        or account.pk == actor.pk
    ):
        raise PermissionDenied("Esta cuenta está protegida.")


@admin_required
@require_http_methods(["GET", "POST", "HEAD"])
def edit(request, pk):
    if request.method == "POST":
        with transaction.atomic():
            accounts = {
                account.pk: account
                for account in User.objects.select_for_update()
                .filter(pk__in=(request.user.pk, pk))
                .order_by("pk")
            }
            if pk not in accounts:
                raise Http404
            account = accounts[pk]
            _require_editable(accounts.get(request.user.pk), account)
            form = AccountEditForm(request.POST, instance=account)
            if form.is_valid():
                account = form.save(commit=False)
                account.save(update_fields=tuple(form.fields))
                messages.success(request, "Cuenta actualizada.")
                return redirect("administration:users")
    else:
        account = get_object_or_404(User, pk=pk)
        _require_editable(request.user, account)
        form = AccountEditForm(instance=account)
    return _render_form(request, form, f"Editar cuenta de {account.username}")


def _render_form(request, form, title):
    return render(request, "administration/form.html", {"form": form, "title": title})
