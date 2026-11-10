from django.contrib import admin
from web.admin import HistoryAdmin
from .models import MaintenancePlan, MaintenanceJob


@admin.register(MaintenancePlan)
class PlanAdmin(HistoryAdmin):
    list_display = ("asset", "due_at", "due_hours")
    search_fields = ("asset__code", "asset__name")
    list_filter = ("due_at",)
    list_select_related = ("asset",)


@admin.register(MaintenanceJob)
class JobAdmin(HistoryAdmin):
    list_display = ("asset", "started_at", "finished_at", "actor", "finished_by")
    search_fields = ("asset__code", "asset__name", "notes")
    list_filter = ("started_at", "finished_at")
    list_select_related = ("asset", "actor", "finished_by")
