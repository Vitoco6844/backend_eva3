from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.views import (
    ContractorViewSet,
    SiteViewSet,
    WarehouseViewSet,
    CategoryViewSet,
    AssetViewSet,
)
from rentals.views import LoanViewSet
from maintenance.views import PlanViewSet, JobViewSet
from payments.views import ChargeViewSet

router = DefaultRouter()
for name, view in [
    ("contractors", ContractorViewSet),
    ("sites", SiteViewSet),
    ("warehouses", WarehouseViewSet),
    ("categories", CategoryViewSet),
    ("assets", AssetViewSet),
    ("loans", LoanViewSet),
    ("maintenance-plans", PlanViewSet),
    ("maintenance-jobs", JobViewSet),
    ("charges", ChargeViewSet),
]:
    router.register(name, view, basename=name)
urlpatterns = [path("", include(router.urls))]
