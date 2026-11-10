from django.urls import path
from . import views as v
from . import storefront, selection
from inventory.images import tool_image
from rentals import request_views as rv

urlpatterns = [
    path("", storefront.home),
    path("panel/", v.dashboard),
    path("mis-solicitudes/", rv.mine),
    path("mis-solicitudes/<int:pk>/", rv.detail),
    path("mis-solicitudes/<int:pk>/cancelar/", rv.cancel),
    path("solicitudes/", rv.inbox),
    path("solicitudes/<int:pk>/entregar/", rv.fulfill),
    path("solicitudes/<int:pk>/rechazar/", rv.reject),
    path("mi-solicitud/", selection.selection),
    path("mi-solicitud/agregar/<int:pk>/", selection.add),
    path("mi-solicitud/quitar/<int:pk>/", selection.remove),
    path("mi-solicitud/vaciar/", selection.clear),
    path("mi-solicitud/enviar/", selection.submit),
    path("mi-solicitud/estimar/", selection.estimate),
    path("catalogo/", storefront.catalog),
    path("catalogo/herramientas/<int:pk>/", storefront.tool),
    path("catalogo/herramientas/<int:pk>/imagen/", tool_image),
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
