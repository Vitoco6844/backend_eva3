from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from accounts.permissions import OperatorPermission
from .models import MaintenancePlan, MaintenanceJob
from .serializers import (
    PlanSerializer,
    JobSerializer,
    StartSerializer,
    FinishSerializer,
)
from .services import start_maintenance, finish_maintenance, save_plan


class PlanViewSet(viewsets.ModelViewSet):
    permission_classes = [OperatorPermission]
    queryset = MaintenancePlan.objects.select_related("asset").order_by("pk")
    serializer_class = PlanSerializer

    def perform_create(self, serializer):
        data = serializer.validated_data
        serializer.instance = save_plan(
            asset_id=data["asset"].pk,
            due_at=data.get("due_at"),
            due_hours=data.get("due_hours"),
            actor=self.request.user,
        )

    def perform_update(self, serializer):
        data = serializer.validated_data
        plan = serializer.instance
        if "asset" in data and data["asset"].pk != plan.asset_id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("No se cambia el activo de un plan existente.")
        serializer.instance = save_plan(
            asset_id=plan.asset_id,
            due_at=data.get("due_at", plan.due_at),
            due_hours=data.get("due_hours", plan.due_hours),
            actor=self.request.user,
        )

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError

        raise ValidationError(
            "Conserva el plan preventivo y actualiza sus próximos límites."
        )


class JobViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [OperatorPermission]
    queryset = MaintenanceJob.objects.select_related("asset").order_by("-pk")
    serializer_class = JobSerializer

    def create(self, request):
        form = StartSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        return Response(
            JobSerializer(
                start_maintenance(**form.validated_data, actor=request.user)
            ).data,
            status=201,
        )

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        form = FinishSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        return Response(
            JobSerializer(
                finish_maintenance(
                    job_id=self.get_object().pk,
                    actor=request.user,
                    **form.validated_data,
                )
            ).data
        )
