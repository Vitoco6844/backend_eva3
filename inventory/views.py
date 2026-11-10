from django.db import transaction
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import OperatorPermission
from . import models, serializers as schema
from .services import transfer_asset, retire_asset


class MasterViewSet(viewsets.ModelViewSet):
    permission_classes = [OperatorPermission]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        self.queryset.model.objects.select_for_update().get(pk=kwargs["pk"])
        return super().update(request, *args, **kwargs)


class ContractorViewSet(MasterViewSet):
    queryset = models.Contractor.objects.all()
    serializer_class = schema.ContractorSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and not request.user.is_superuser
            and request.user.role != "ADMIN"
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Solo administración gestiona contratistas.")


class SiteViewSet(MasterViewSet):
    queryset = models.Site.objects.all()
    serializer_class = schema.SiteSerializer


class WarehouseViewSet(MasterViewSet):
    queryset = models.Warehouse.objects.select_related("site")
    serializer_class = schema.WarehouseSerializer


class CategoryViewSet(MasterViewSet):
    queryset = models.Category.objects.all()
    serializer_class = schema.CategorySerializer


class AssetViewSet(MasterViewSet):
    queryset = models.Asset.objects.select_related("warehouse", "category")
    serializer_class = schema.AssetSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        if self.request.query_params.get("q"):
            qs = qs.filter(name__icontains=self.request.query_params["q"])
        return qs

    def perform_create(self, serializer):
        asset = serializer.save()
        from .services import record_event

        record_event(asset, self.request.user, "", "ALTA", "Alta en catálogo")

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        class Input(serializers.Serializer):
            warehouse_id = serializers.PrimaryKeyRelatedField(
                queryset=models.Warehouse.objects.all()
            )
            reason = serializers.CharField(max_length=1000)

        data = Input(data=request.data)
        data.is_valid(raise_exception=True)
        asset = transfer_asset(
            asset_id=self.get_object().pk,
            warehouse_id=data.validated_data["warehouse_id"].pk,
            actor=request.user,
            reason=data.validated_data["reason"],
        )
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        reason = request.data.get("reason", "")
        if not isinstance(reason, str):
            raise serializers.ValidationError("Motivo inválido")
        return Response(
            self.get_serializer(
                retire_asset(
                    asset_id=self.get_object().pk, actor=request.user, reason=reason
                )
            ).data
        )
