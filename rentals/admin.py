from django.contrib import admin
from web.admin import HistoryAdmin
from .models import Loan, LoanItem, Signature, OverdueAlert


@admin.register(Loan)
class LoanAdmin(HistoryAdmin):
    list_display = (
        "id",
        "contractor",
        "site",
        "responsible",
        "issued_at",
        "due_at",
        "closed_at",
    )
    search_fields = ("contractor__name", "responsible")
    list_filter = ("site", "issued_at", "due_at")
    list_select_related = ("contractor", "site")


@admin.register(LoanItem)
class LoanItemAdmin(HistoryAdmin):
    list_display = (
        "loan",
        "asset",
        "returned_at",
        "daily_rate",
        "usage_hours",
        "damaged",
    )
    search_fields = ("asset__code", "asset__name")
    list_filter = ("damaged", "returned_at")
    list_select_related = ("loan", "asset")


@admin.register(Signature)
class SignatureAdmin(HistoryAdmin):
    list_display = ("loan", "kind", "name", "actor", "at", "digest")
    search_fields = ("name", "digest")
    list_filter = ("kind", "at")
    list_select_related = ("loan", "actor")
    exclude = ("image",)

    def get_readonly_fields(self, request, obj=None):
        return [f for f in super().get_readonly_fields(request, obj) if f != "image"]


@admin.register(OverdueAlert)
class AlertAdmin(HistoryAdmin):
    list_display = ("loan", "detected_at", "resolved_at")
    search_fields = ("loan__contractor__name",)
    list_filter = ("detected_at", "resolved_at")
    list_select_related = ("loan",)


from .models import RentalRequest, RentalRequestItem


@admin.register(RentalRequest)
class RentalRequestAdmin(HistoryAdmin):
    list_display = (
        "id",
        "contractor",
        "site_name",
        "starts_at",
        "ends_at",
        "status",
        "created_at",
    )
    search_fields = ("contractor__name", "site_name", "responsible")
    list_filter = ("status", "starts_at", "created_at")
    list_select_related = ("contractor",)


@admin.register(RentalRequestItem)
class RentalRequestItemAdmin(HistoryAdmin):
    list_display = ("request", "asset", "estimated_daily_rate")
    search_fields = ("asset__name", "asset__code")
    list_filter = ("asset__category",)
    list_select_related = ("request", "asset")


from .models import AssetHold


@admin.register(AssetHold)
class AssetHoldAdmin(HistoryAdmin):
    list_display = ("asset", "request", "created_at")
    list_select_related = ("asset", "request")
    search_fields = ("asset__code", "request__contractor__name")
