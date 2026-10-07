from dataclasses import FrozenInstanceError

from django.test import SimpleTestCase

from payments.gateways.base import GatewayResult, PaymentGateway


class PaymentGatewayTests(SimpleTestCase):
    def test_cannot_instantiate_without_charge(self):
        with self.assertRaises(TypeError):
            PaymentGateway()

    def test_charge_must_be_implemented_by_subclass(self):
        class Incomplete(PaymentGateway):
            name = "incomplete"

        with self.assertRaises(TypeError):
            Incomplete()

    def test_charge_signature_requires_keyword_arguments(self):
        class Stub(PaymentGateway):
            name = "stub"

            def charge(self, *, amount, reference, idempotency_key):
                return GatewayResult(
                    success=True,
                    external_ref="ref-1",
                    raw={"echo": idempotency_key},
                )

        result = Stub().charge(
            amount="100.00", reference="req-1", idempotency_key="ik-1"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.external_ref, "ref-1")
        self.assertEqual(result.raw, {"echo": "ik-1"})

    def test_name_is_reported(self):
        class Stub(PaymentGateway):
            name = "stub"

            def charge(self, *, amount, reference, idempotency_key):
                raise NotImplementedError

        self.assertEqual(Stub.name, "stub")


class GatewayResultTests(SimpleTestCase):
    def test_defaults(self):
        result = GatewayResult(success=False, external_ref="")
        self.assertFalse(result.success)
        self.assertEqual(result.external_ref, "")
        self.assertEqual(result.message, "")
        self.assertEqual(result.raw, {})

    def test_is_frozen(self):
        result = GatewayResult(success=True, external_ref="ref")
        with self.assertRaises(FrozenInstanceError):
            result.success = False