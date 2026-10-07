"""Payment execution service.

``execute_payment`` is the idempotent entry point for charging an approved
payment request through the configured gateway adapter. Replaying a call with
the same ``idempotency_key`` returns the original result and never charges the
gateway twice -- the unique constraint on ``PaymentTransaction.idempotency_key``
is the guarantee.
"""
from uuid import uuid4

from django.db import IntegrityError, transaction

from payments.gateways.registry import get_gateway
from payments.models import PaymentRequest, PaymentTransaction

# A request can be charged when approved, or retried after a failed attempt.
PAYABLE_STATUSES = (PaymentRequest.APPROVED, PaymentRequest.FAILED)


class PaymentNotPayable(Exception):
    """Raised when a request cannot be charged in its current state."""

    def __init__(self, request):
        super().__init__(
            f"PaymentRequest {request.id} is not payable in status "
            f"{request.status!r}"
        )


def execute_payment(payment_request, *, idempotency_key=None) -> PaymentTransaction:
    """Charge ``payment_request`` exactly once for the given key.

    Returns the ``PaymentTransaction`` either way (new charge or replay).
    """
    key = idempotency_key or str(uuid4())

    with transaction.atomic():
        existing = PaymentTransaction.objects.filter(idempotency_key=key).first()
        if existing is not None:
            return existing

        if payment_request.status not in PAYABLE_STATUSES:
            raise PaymentNotPayable(payment_request)

        gateway = get_gateway()
        try:
            with transaction.atomic():
                txn = PaymentTransaction.objects.create(
                    request=payment_request,
                    gateway=gateway.name,
                    idempotency_key=key,
                    amount=payment_request.amount,
                    status=PaymentTransaction.PROCESSING,
                )
        except IntegrityError:
            # Another request won the race for this key; replay its result.
            return (
                PaymentTransaction.objects.select_for_update()
                .get(idempotency_key=key)
            )

        result = gateway.charge(
            amount=str(payment_request.amount),
            reference=str(payment_request.id),
            idempotency_key=key,
        )

        txn.status = (
            PaymentTransaction.SUCCESS if result.success else PaymentTransaction.FAILED
        )
        txn.external_ref = result.external_ref
        txn.gateway_response = result.raw
        txn.save(update_fields=["status", "external_ref", "gateway_response", "updated_at"])

        payment_request.status = (
            PaymentRequest.PAID if result.success else PaymentRequest.FAILED
        )
        payment_request.save(update_fields=["status", "updated_at"])
        return txn