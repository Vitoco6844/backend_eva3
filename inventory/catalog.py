import unicodedata
from django.urls import reverse
from .models import Asset
from maintenance.services import is_due


def public_assets():
    return (
        Asset.objects.filter(
            category__active=True, warehouse__active=True, warehouse__site__active=True
        )
        .exclude(status="BAJA")
        .select_related("category", "warehouse__site")
    )


def available_for_request(asset, at=None):
    return (
        asset.status == "DISPONIBLE"
        and asset.category.active
        and asset.warehouse.active
        and asset.warehouse.site.active
        and not is_due(asset, at)
    )


def family_image(asset):
    tool = (
        unicodedata.normalize("NFKD", asset.name)
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )
    for term, key in [
        ("taladro inalambrico", "taladro-inalambrico"),
        ("taladro", "taladro-percutor"),
        ("esmeril", "esmeril"),
        ("caladora", "caladora"),
        ("vibrador", "vibrador"),
    ]:
        if term in tool:
            return key

    name = (
        unicodedata.normalize("NFKD", asset.category.name)
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )
    for term, key in [
        ("corte", "corte"),
        ("compact", "compactacion"),
        ("hormig", "hormigonado"),
        ("medic", "medicion"),
        ("energia", "energia"),
        ("sold", "soldadura"),
    ]:
        if term in name:
            return key
    return "perforacion"


def prepare_asset(asset):
    asset.requestable = available_for_request(asset)
    asset.public_availability = (
        "Disponible hoy" if asset.requestable else "Temporalmente no disponible"
    )
    asset.catalog_image_url = f"/catalogo/herramientas/{asset.pk}/imagen/"
    return asset
