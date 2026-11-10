from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS


def can_operate(user):
    return bool(
        user.is_authenticated
        and user.is_active
        and (user.is_superuser or user.role in ("ADMIN", "BODEGUERO"))
    )


def require_operator(user):
    if not can_operate(user):
        raise PermissionDenied("Solo administradores y bodegueros pueden operar.")


def contractor_scope(user, queryset, field="contractor_id"):
    if can_operate(user):
        return queryset
    if not user.is_authenticated or not user.is_active or not user.contractor_id:
        return queryset.none()
    return queryset.filter(**{field: user.contractor_id})


class OperatorPermission(BasePermission):
    def has_permission(self, request, view):
        return can_operate(request.user)
