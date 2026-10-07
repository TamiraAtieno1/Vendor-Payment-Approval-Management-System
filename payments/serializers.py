from rest_framework import serializers

from .models import PaymentRequest, PaymentTransaction


class PaymentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequest
        fields = [
            "id",
            "vendor",
            "project",
            "amount",
            "description",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "request",
            "gateway",
            "idempotency_key",
            "external_ref",
            "amount",
            "status",
            "gateway_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PayRequestSerializer(serializers.Serializer):
    """Body of POST .../pay/: the client's idempotency key (optional)."""

    idempotency_key = serializers.CharField(
        required=False, allow_blank=False, max_length=255
    )