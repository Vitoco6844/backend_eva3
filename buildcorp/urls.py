from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path, include
from payments.views import webpay_return

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth.LoginView.as_view()),
    path("accounts/logout/", auth.LogoutView.as_view()),
    path("payments/return/", webpay_return),
    path("api/", include("web.urls_api")),
    path("", include("web.urls")),
]
admin.site.site_header = "BuildCorp · Administración"
admin.site.site_title = "BuildCorp"
admin.site.index_title = "Gestión de activos y operaciones"
