from rest_framework import serializers
from .models import Charge, PaymentAttempt


class ChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charge
        fields = [
            "id",
            "loan",
            "rental_request",
            "kind",
            "amount",
            "created_at",
            "paid_at",
            "voided_at",
        ]


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = [
            "id",
            "charge",
            "order",
            "amount",
            "status",
            "response_code",
            "authorization",
            "created_at",
        ]
