from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from payments.gateways.base import GatewayResult
from payments.models import PaymentRequest, PaymentTransaction, Vendor
from payments.services import PaymentNotPayable, execute_payment


class RecordingGateway:
    """Fake gateway that records charge calls and returns a fixed outcome."""

    def __init__(self, result):
        self.name = "recording"
        self.result = result
        self.calls = []

    def charge(self, *, amount, reference, idempotency_key):
        self.calls.append((amount, reference, idempotency_key))
        return self.result


def patch_gateway(result):
    gateway = RecordingGateway(result)
    gateway.patch = patch("payments.services.get_gateway", return_value=gateway)
    return gateway, gateway.patch


class ExecutePaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carol", password="x")
        self.vendor = Vendor.objects.create(name="Acme", service="Cleaning")
        self.request = PaymentRequest.objects.create(
            vendor=self.vendor,
            amount=Decimal("2500.00"),
            status=PaymentRequest.APPROVED,
            created_by=self.user,
        )

    def _execute(self, gateway, key="key-1"):
        with gateway.patch:
            return execute_payment(self.request, idempotency_key=key)

    def test_paying_approved_request_marks_request_paid(self):
        gateway, _ = patch_gateway(
            GatewayResult(success=True, external_ref="mock-abc")
        )
        txn = self._execute(gateway)

        self.request.refresh_from_db()
        self.assertEqual(self.request.status, PaymentRequest.PAID)
        self.assertEqual(
            PaymentTransaction.objects.filter(request=self.request).count(), 1
        )
        self.assertEqual(txn.status, PaymentTransaction.SUCCESS)
        self.assertEqual(txn.external_ref, "mock-abc")

    def test_gateway_receives_amount_and_reference(self):
        gateway, _ = patch_gateway(
            GatewayResult(success=True, external_ref="mock-abc")
        )
        self._execute(gateway)

        amount, reference, _ = gateway.calls[0]
        self.assertEqual(amount, "2500.00")
        self.assertEqual(reference, str(self.request.id))

    def test_same_key_replays_without_recharging(self):
        gateway, _ = patch_gateway(
            GatewayResult(success=True, external_ref="mock-abc")
        )
        first = self._execute(gateway, key="same-key")
        second = self._execute(gateway, key="same-key")

        self.assertEqual(first.id, second.id)
        self.assertEqual(len(gateway.calls), 1)
        self.assertEqual(
            PaymentTransaction.objects.filter(request=self.request).count(), 1
        )
        self.assertEqual(first.status, PaymentTransaction.SUCCESS)

    def test_replay_returns_existing_transaction_when_request_not_payable(self):
        existing = PaymentTransaction.objects.create(
            request=self.request,
            gateway="mock",
            idempotency_key="key-1",
            amount=self.request.amount,
            status=PaymentTransaction.SUCCESS,
        )
        gateway, _ = patch_gateway(
            GatewayResult(success=True, external_ref="other")
        )
        self.request.status = PaymentRequest.DRAFT
        self.request.save()

        with gateway.patch:
            result = execute_payment(self.request, idempotency_key="key-1")

        self.assertEqual(result.id, existing.id)
        self.assertEqual(len(gateway.calls), 0)

    def test_auto_generated_key_when_none_given(self):
        gateway, _ = patch_gateway(
            GatewayResult(success=True, external_ref="mock-abc")
        )
        with gateway.patch:
            txn = execute_payment(self.request)
        self.assertTrue(txn.idempotency_key)

    def test_declined_payment_marks_request_failed(self):
        gateway, _ = patch_gateway(
            GatewayResult(success=False, external_ref="", message="Declined")
        )
        txn = self._execute(gateway)

        self.assertEqual(txn.status, PaymentTransaction.FAILED)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, PaymentRequest.FAILED)

    def test_failed_request_can_be_retried_with_new_key(self):
        gateway, _ = patch_gateway(
            GatewayResult(success=False, external_ref="", message="Declined")
        )
        self._execute(gateway, key="try-1")
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, PaymentRequest.FAILED)

        gateway2, _ = patch_gateway(
            GatewayResult(success=True, external_ref="mock-xyz")
        )
        with gateway2.patch:
            txn = execute_payment(self.request, idempotency_key="try-2")
        self.assertEqual(txn.status, PaymentTransaction.SUCCESS)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, PaymentRequest.PAID)

    def test_non_approved_request_is_rejected(self):
        for status in (
            PaymentRequest.DRAFT,
            PaymentRequest.PENDING,
            PaymentRequest.REJECTED,
            PaymentRequest.PAID,
        ):
            self.request.status = status
            self.request.save()
            gateway, _ = patch_gateway(
                GatewayResult(success=True, external_ref="mock-abc")
            )
            with self.subTest(status=status), gateway.patch:
                with self.assertRaises(PaymentNotPayable):
                    execute_payment(self.request, idempotency_key=f"key-{status}")
            self.assertEqual(len(gateway.calls), 0)
        self.assertEqual(
            PaymentTransaction.objects.filter(request=self.request).count(), 0
        )