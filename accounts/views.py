from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.utils.http import url_has_allowed_host_and_scheme
from .permissions import can_operate
from .forms import CustomerRegistrationForm
from .services import register_customer


def safe_next(request, default="/mis-solicitudes/"):
    value = request.POST.get("next") or request.GET.get("next", "")
    return (
        value
        if url_has_allowed_host_and_scheme(
            value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        )
        else default
    )


class RoleLoginView(LoginView):
    def get_default_redirect_url(self):
        return "/panel/" if can_operate(self.request.user) else "/mis-solicitudes/"


def register(request):
    if request.user.is_authenticated:
        return redirect("/panel/" if can_operate(request.user) else "/mis-solicitudes/")
    form = CustomerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            user = register_customer(
                username=data["username"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                tax_id=data["tax_id"],
                company_name=data["company_name"],
                phone=data["phone"],
                password=data["password1"],
            )
            login(request, user)
            return redirect(safe_next(request))
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
    return render(
        request, "public/register.html", {"form": form, "next": safe_next(request)}
    )
