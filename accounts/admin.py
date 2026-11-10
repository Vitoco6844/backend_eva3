from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class BuildUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("BuildCorp", {"fields": ("role", "contractor")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("BuildCorp", {"fields": ("role", "contractor")}),
    )
    list_display = ("username", "email", "role", "contractor", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "contractor__name")

    def has_module_permission(self, request):
        return request.user.is_superuser or (
            request.user.role == "ADMIN" and super().has_module_permission(request)
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request) and super().has_view_permission(
            request, obj
        )

    def has_add_permission(self, request):
        return self.has_module_permission(request) and super().has_add_permission(
            request
        )

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request) and super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request) and super().has_delete_permission(
            request, obj
        )
