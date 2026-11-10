from django.urls import path
from . import views as v

urlpatterns = [
    path("", v.dashboard),
    path("inventory/<str:kind>/", v.master_list),
    path("inventory/<str:kind>/new/", v.master_form),
    path("inventory/<str:kind>/<int:pk>/edit/", v.master_form),
    path("inventory/<str:kind>/<int:pk>/delete/", v.master_delete),
    path("inventory/assets/<int:pk>/", v.asset_detail),
    path("inventory/assets/<int:pk>/<str:action>/", v.asset_action),
    path("rentals/", v.loans),
    path("rentals/new/", v.issue),
    path("rentals/<int:pk>/", v.loan_detail),
    path("rentals/<int:pk>/return/", v.return_loan),
    path("signatures/<int:pk>/", v.signature_image),
    path("maintenance/", v.maintenance),
    path("maintenance/<str:action>/", v.maintenance_form),
    path("maintenance/<str:action>/<int:pk>/", v.maintenance_form),
    path("alerts/", v.alerts),
    path("payments/", v.charges),
    path("payments/<int:pk>/", v.charge_detail),
    path("payments/<int:pk>/continue/", v.payment_continue),
]
