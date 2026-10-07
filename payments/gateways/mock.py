"""Deterministic mock payment provider for development and tests.

The whole point of the mock is to be *predictable*: you control the outcome
by naming the charge. An amount or reference containing ``FAIL`` (case
insensitive) is declined; everything else is approved.

It also honours idempotency at its own layer: the first charge for a given
``idempotency_key`` is recorded and every later call for the same key returns
the exact same result, so a retried charge can never bill twice.
"""
from uuid import uuid4

from payments.gateways.base import GatewayResult, PaymentGateway

FAIL_MARKER = "FAIL"


class MockPaymentGateway(PaymentGateway):
    name = "mock"

    def __init__(self):
        self._results = {}

    def charge(self, *, amount, reference, idempotency_key) -> GatewayResult:
        if idempotency_key in self._results:
            return self._results[idempotency_key]

        failed = FAIL_MARKER in f"{amount} {reference}".upper()
        result = GatewayResult(
            success=not failed,
            external_ref="" if failed else f"mock-{uuid4().hex[:8]}",
            message="Simulated decline" if failed else "Payment approved",
            raw={
                "amount": str(amount),
                "reference": reference,
                "idempotency_key": idempotency_key,
            },
        )
        self._results[idempotency_key] = result
        return result