from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from rest_framework.decorators import api_view
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PaymentRequest, PaymentTransaction
from .serializers import (
    PaymentRequestSerializer,
    PaymentTransactionSerializer,
    PayRequestSerializer,
)
from .services import PaymentNotPayable, execute_payment


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok'})


class PaymentRequestListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentRequestSerializer
    queryset = PaymentRequest.objects.select_related(
        "vendor", "project", "created_by"
    ).all()


class PaymentRequestPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        payment_request = get_object_or_404(PaymentRequest, pk=pk)

        body = PayRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        key = body.validated_data.get("idempotency_key")
        replayed = (
            key is not None
            and PaymentTransaction.objects.filter(idempotency_key=key).exists()
        )

        try:
            txn = execute_payment(payment_request, idempotency_key=key)
        except PaymentNotPayable as exc:
            return Response(
                {"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST
            )

        payload = PaymentTransactionSerializer(txn).data
        payload["replayed"] = replayed
        return Response(payload, status=http_status.HTTP_200_OK)