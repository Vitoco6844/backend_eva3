from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.urls import path
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.administration import (
    AccountEditForm,
    StaffCreationForm,
    _require_editable,
)
from accounts.models import User
from accounts.permissions import can_administer, can_operate
from inventory.models import Asset, Contractor
from inventory.views import (
    AssetViewSet,
    CategoryViewSet,
    ContractorViewSet,
    SiteViewSet,
    WarehouseViewSet,
)
from maintenance.views import JobViewSet, PlanViewSet
from payments.models import Charge
from payments.serializers import ChargeSerializer
from rentals.approval_services import create_operator_request
from rentals.models import Loan
from rentals.request_api import RentalRequestViewSet
from rentals.request_serializers import SubmitRequestSerializer
from rentals.views import LoanViewSet


class StaffTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if not can_operate(self.user):
            raise PermissionDenied("El acceso es exclusivo de personal de BuildCorp.")
        return data


class StaffLogin(TokenObtainPairView):
    serializer_class = StaffTokenSerializer


class InternalRequestInput(SubmitRequestSerializer):
    contractor_id = serializers.PrimaryKeyRelatedField(
        queryset=Contractor.objects.all()
    )


class InternalRequests(RentalRequestViewSet):
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not self.get_object().internal:
            raise ValidationError(
                {"detail": "Solo se aprueban solicitudes internas en EVA 4."}
            )
        return super().approve(request, pk)

    def create(self, request):
        form = InternalRequestInput(data=request.data)
        form.is_valid(raise_exception=True)
        data = dict(form.validated_data)
        data["contractor_id"] = data["contractor_id"].pk
        obj = create_operator_request(actor=request.user, internal=True, **data)
        return Response(self.get_serializer(obj).data, status=201)


class HistoricalCharges(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = ChargeSerializer
    queryset = Charge.objects.order_by("-pk")


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "is_superuser",
        )


class Users(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AccountSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not can_administer(request.user):
            raise PermissionDenied

    def get_queryset(self):
        q = self.request.query_params.get("q", "").strip()[:150]
        return User.objects.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        ).order_by("username", "pk")

    @transaction.atomic
    def create(self, request):
        actor = User.objects.select_for_update().get(pk=request.user.pk)
        if not can_administer(actor):
            raise PermissionDenied
        form = StaffCreationForm(request.data)
        if not form.is_valid():
            raise ValidationError(form.errors.get_json_data())
        try:
            with transaction.atomic():
                account = form.save()
        except IntegrityError as exc:
            raise ValidationError(
                {"detail": "El usuario o correo ya está en uso."}
            ) from exc
        return Response(self.get_serializer(account).data, status=201)

    @transaction.atomic
    def partial_update(self, request, pk=None):
        if not pk.isdecimal():
            raise Http404
        accounts = {
            str(u.pk): u
            for u in User.objects.select_for_update()
            .filter(pk__in=[request.user.pk, pk])
            .order_by("pk")
        }
        if pk not in accounts:
            raise Http404
        account = accounts[pk]
        _require_editable(accounts.get(str(request.user.pk)), account)
        editable = AccountEditForm(instance=account).fields
        if set(request.data) - set(editable):
            raise ValidationError({"detail": "Campo no editable."})
        data = {
            field: request.data.get(field, getattr(account, field))
            for field in editable
        }
        form = AccountEditForm(data, instance=account)
        if not form.is_valid():
            raise ValidationError(form.errors.get_json_data())
        account = form.save(commit=False)
        account.save(update_fields=list(editable))
        return Response(self.get_serializer(account).data)


@api_view(["GET"])
def me(request):
    return Response(AccountSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def overview(request):
    loans = Loan.objects.filter(closed_at=None)
    return Response(
        {
            "available": Asset.objects.filter(
                status="DISPONIBLE", rental_hold__isnull=True
            ).count(),
            "open_count": loans.count(),
            "overdue_count": loans.filter(due_at__lt=timezone.now()).count(),
            "pending_count": Charge.objects.filter(
                paid_at=None, voided_at=None
            ).count(),
            "loans": list(
                loans.order_by("-pk").values(
                    "id", "contractor__name", "site__name", "due_at"
                )[:6]
            ),
        }
    )


@api_view(["GET"])
def alerts(request):
    now = timezone.now()
    overdue = Loan.objects.filter(closed_at=None, due_at__lt=now).order_by("due_at")
    blocked = (
        Contractor.objects.filter(
            Q(manual_block=True) | Q(loan__closed_at=None, loan__due_at__lt=now)
        )
        .distinct()
        .order_by("name")
    )
    return Response(
        {
            "overdue": list(overdue.values("id", "contractor__name", "due_at")),
            "blocked": list(blocked.values("id", "name")),
        }
    )


router = DefaultRouter()
for name, view in {
    "sites": SiteViewSet,
    "warehouses": WarehouseViewSet,
    "categories": CategoryViewSet,
    "assets": AssetViewSet,
    "contractors": ContractorViewSet,
    "rental-requests": InternalRequests,
    "loans": LoanViewSet,
    "maintenance-plans": PlanViewSet,
    "maintenance-jobs": JobViewSet,
    "charges": HistoricalCharges,
    "users": Users,
}.items():
    router.register(name, view, basename=name)

urlpatterns = [
    path("auth/token/", StaffLogin.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", me),
    path("health/", health),
    path("alerts/", alerts),
    path("overview/", overview),
    *router.urls,
]
