from rest_framework import serializers
from inventory.models import Site
from .models import RentalRequest, RentalRequestItem


class RequestItemSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = RentalRequestItem
        fields = [
            "id",
            "asset",
            "asset_name",
            "estimated_daily_rate",
            "approved_daily_rate",
        ]


class RentalRequestSerializer(serializers.ModelSerializer):
    items = RequestItemSerializer(many=True, read_only=True)
    contractor_name = serializers.CharField(source="contractor.name", read_only=True)

    class Meta:
        model = RentalRequest
        fields = [
            "id",
            "contractor_name",
            "site_name",
            "site_address",
            "responsible",
            "starts_at",
            "ends_at",
            "notes",
            "estimated_amount",
            "approved_amount",
            "approved_at",
            "status",
            "created_at",
            "resolution_reason",
            "loan",
            "items",
        ]


class SubmitRequestSerializer(serializers.Serializer):
    asset_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, max_length=20
    )
    site_name = serializers.CharField(max_length=140)
    site_address = serializers.CharField(max_length=250)
    responsible = serializers.CharField(max_length=140)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    notes = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )
    submit_key = serializers.UUIDField()

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: "Campo no permitido." for key in unknown}
            )
        return super().to_internal_value(data)


class FulfillSerializer(serializers.Serializer):
    responsible = serializers.CharField(max_length=140)
    signature = serializers.CharField(max_length=350000)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {
                    key: "La entrega utiliza exclusivamente la cotización ya pagada."
                    for key in unknown
                }
            )
        return super().to_internal_value(data)
