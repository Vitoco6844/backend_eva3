from django.contrib import admin
from django.db import transaction
from accounts.permissions import can_operate


class BusinessAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return can_operate(request.user) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return can_operate(request.user) and super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return can_operate(request.user) and super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return can_operate(request.user) and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return bool(
            request.user.is_superuser or request.user.role == "ADMIN"
        ) and super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not change:
            return super().save_model(request, obj, form, change)
        with transaction.atomic():
            locked = type(obj).objects.select_for_update().get(pk=obj.pk)
            for name in form.changed_data:
                if name not in ("groups", "user_permissions"):
                    setattr(locked, name, getattr(obj, name))
            locked.full_clean()
            locked.save(
                update_fields=[
                    n
                    for n in form.changed_data
                    if n not in ("groups", "user_permissions")
                ]
            )


class HistoryAdmin(BusinessAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
