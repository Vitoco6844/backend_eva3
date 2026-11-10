from django.contrib import admin
from django.utils.html import format_html
from web.admin import BusinessAdmin, HistoryAdmin
from .models import Contractor, Site, Warehouse, Category, Asset, AssetEvent
from .services import record_event


@admin.register(Contractor)
class ContractorAdmin(BusinessAdmin):
    list_display = ("name", "tax_id", "active", "manual_block")
    search_fields = ("name", "tax_id", "email")
    list_filter = ("active", "manual_block")

    def has_change_permission(self, request, obj=None):
        return bool(
            request.user.is_superuser or request.user.role == "ADMIN"
        ) and super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return bool(
            request.user.is_superuser or request.user.role == "ADMIN"
        ) and super().has_add_permission(request)


@admin.register(Site)
class SiteAdmin(BusinessAdmin):
    list_display = ("name", "address", "active")
    search_fields = ("name", "address")
    list_filter = ("active",)


@admin.register(Warehouse)
class WarehouseAdmin(BusinessAdmin):
    list_display = ("name", "site", "active")
    search_fields = ("name", "site__name")
    list_filter = ("site", "active")
    list_select_related = ("site",)


@admin.register(Category)
class CategoryAdmin(BusinessAdmin):
    list_display = ("name", "active")
    search_fields = ("name",)
    list_filter = ("active",)


@admin.register(Asset)
class AssetAdmin(BusinessAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "warehouse",
        "status",
        "daily_rate",
        "usage_hours",
    )
    search_fields = ("code", "name", "serial")
    list_filter = ("status", "category", "warehouse")
    list_select_related = ("category", "warehouse")

    def get_readonly_fields(self, request, obj=None):
        return ["status", "usage_hours", "operations"] + (["warehouse"] if obj else [])

    @admin.display(description="Operaciones e historial")
    def operations(self, obj):
        return (
            format_html(
                '<a href="/inventory/assets/{}/">Abrir hoja de vida, traslado y baja</a>',
                obj.pk,
            )
            if obj.pk
            else "Disponible después de crear."
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            record_event(obj, request.user, "", "ALTA", "Alta desde Django Admin")


@admin.register(AssetEvent)
class EventAdmin(HistoryAdmin):
    list_display = ("asset", "kind", "at", "actor", "previous_status", "new_status")
    search_fields = ("asset__code", "asset__name", "reason")
    list_filter = ("kind", "new_status", "at")
    list_select_related = ("asset", "actor")
