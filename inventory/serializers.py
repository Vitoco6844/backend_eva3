from rest_framework import serializers
from .models import Contractor, Site, Warehouse, Category, Asset


class StrictSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        writable = {key for key, value in self.fields.items() if not value.read_only}
        unknown = set(data) - writable
        if unknown:
            raise serializers.ValidationError(
                {key: "Campo no editable o desconocido." for key in unknown}
            )
        return super().to_internal_value(data)


class ContractorSerializer(StrictSerializer):
    class Meta:
        model = Contractor
        fields = "__all__"


class SiteSerializer(StrictSerializer):
    class Meta:
        model = Site
        fields = "__all__"


class WarehouseSerializer(StrictSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"


class CategorySerializer(StrictSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class AssetSerializer(StrictSerializer):
    class Meta:
        model = Asset
        fields = "__all__"
        read_only_fields = ["status", "usage_hours"]

    def validate(self, data):
        if self.instance and "warehouse" in data:
            raise serializers.ValidationError(
                "Utiliza la acción de traslado para cambiar de bodega."
            )
        return data
