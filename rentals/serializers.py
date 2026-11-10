from rest_framework import serializers
from .models import Loan, LoanItem, Signature
from inventory.models import Asset, Contractor, Site


class LoanItemSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = LoanItem
        fields = [
            "id",
            "asset",
            "asset_name",
            "daily_rate",
            "returned_at",
            "usage_hours",
            "damaged",
            "notes",
        ]


class LoanSerializer(serializers.ModelSerializer):
    items = LoanItemSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id",
            "contractor",
            "site",
            "responsible",
            "issued_at",
            "due_at",
            "closed_at",
            "billing_mode",
            "items",
        ]


class IssueSerializer(serializers.Serializer):
    request_id = serializers.IntegerField(min_value=1)
    responsible = serializers.CharField(max_length=140)
    signature = serializers.CharField(max_length=350000)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "La entrega requiere request_id de una solicitud pagada; la tarifa y fechas no se envían nuevamente."
                    ]
                }
            )
        return super().to_internal_value(data)


class ReturnLineSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)
    usage_hours = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    damaged = serializers.BooleanField(default=False)
    notes = serializers.CharField(max_length=2000, allow_blank=True, default="")


class ReturnSerializer(serializers.Serializer):
    items = ReturnLineSerializer(many=True, allow_empty=False)
    signature = serializers.CharField(max_length=350000)
