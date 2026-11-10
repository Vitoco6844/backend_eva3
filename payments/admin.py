from django.contrib import admin
from web.admin import HistoryAdmin
from .models import Charge, PaymentAttempt


@admin.register(Charge)
class ChargeAdmin(HistoryAdmin):
    list_display = ("id", "loan", "amount", "created_at", "paid_at")
    search_fields = ("loan__contractor__name",)
    list_filter = ("paid_at", "created_at")
    list_select_related = ("loan",)


@admin.register(PaymentAttempt)
class AttemptAdmin(HistoryAdmin):
    list_display = (
        "order",
        "charge",
        "amount",
        "status",
        "response_code",
        "created_at",
    )
    search_fields = ("order", "authorization", "charge__loan__contractor__name")
    list_filter = ("status", "created_at")
    list_select_related = ("charge",)

    def get_readonly_fields(self, request, obj=None):
        return [
            f
            for f in super().get_readonly_fields(request, obj)
            if f not in ("token", "redirect_url")
        ]

    exclude = ("token", "redirect_url")
