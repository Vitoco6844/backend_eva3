from rest_framework import serializers
from .models import MaintenancePlan, MaintenanceJob


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenancePlan
        fields = "__all__"


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceJob
        fields = "__all__"


class StartSerializer(serializers.Serializer):
    asset_id = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(max_length=2000)


class FinishSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=2000)
    next_due_at = serializers.DateTimeField(
        required=False, allow_null=True, default=None
    )
    next_due_hours = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
        min_value=0,
    )
