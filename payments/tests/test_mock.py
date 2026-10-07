from django.test import SimpleTestCase

from payments.gateways.mock import MockPaymentGateway


class MockPaymentGatewayTests(SimpleTestCase):
    def setUp(self):
        self.gateway = MockPaymentGateway()

    def test_name_is_mock(self):
        self.assertEqual(self.gateway.name, "mock")

    def test_successful_charge_returns_external_ref(self):
        result = self.gateway.charge(
            amount="1000.00", reference="req-1", idempotency_key="ik-1"
        )
        self.assertTrue(result.success)
        self.assertTrue(result.external_ref)
        self.assertEqual(result.raw["reference"], "req-1")

    def test_fail_marker_in_amount_declines(self):
        result = self.gateway.charge(
            amount="FAIL", reference="req-1", idempotency_key="ik-1"
        )
        self.assertFalse(result.success)
        self.assertEqual(result.external_ref, "")

    def test_fail_marker_in_reference_declines(self):
        result = self.gateway.charge(
            amount="100.00", reference="FAIL-1", idempotency_key="ik-1"
        )
        self.assertFalse(result.success)

    def test_same_idempotency_key_replays_identical_result(self):
        first = self.gateway.charge(
            amount="1000.00", reference="req-1", idempotency_key="ik-1"
        )
        second = self.gateway.charge(
            amount="1000.00", reference="req-1", idempotency_key="ik-1"
        )
        self.assertEqual(first, second)
        # One distinct charge, no double-billing.
        self.assertEqual(len(self.gateway._results), 1)

    def test_different_keys_are_distinct_charges(self):
        self.gateway.charge(
            amount="100.00", reference="req-1", idempotency_key="ik-1"
        )
        self.gateway.charge(
            amount="100.00", reference="req-1", idempotency_key="ik-2"
        )
        self.assertEqual(len(self.gateway._results), 2)