from django.test import SimpleTestCase, override_settings

from payments.gateways.base import GatewayResult, PaymentGateway
from payments.gateways.registry import get_gateway, register


class EchoGateway(PaymentGateway):
    name = "echo"

    def charge(self, *, amount, reference, idempotency_key) -> GatewayResult:
        return GatewayResult(
            success=True,
            external_ref=f"echo-{reference}",
            raw={"idempotency_key": idempotency_key},
        )


class GatewayRegistryTests(SimpleTestCase):
    @override_settings(PAYMENT_GATEWAY="echo")
    def test_default_gateway_from_settings(self):
        self.assertIsInstance(get_gateway(), EchoGateway)

    def test_get_gateway_by_name(self):
        gateway = get_gateway("echo")
        self.assertIsInstance(gateway, EchoGateway)

    def test_unknown_gateway_raises(self):
        with self.assertRaises(ValueError):
            get_gateway("stripe")

    def test_registered_gateway_works_end_to_end(self):
        result = get_gateway("echo").charge(
            amount="10.00", reference="req-1", idempotency_key="ik-1"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.external_ref, "echo-req-1")

    def test_duplicate_registration_raises(self):
        with self.assertRaises(ValueError):
            register(EchoGateway)


register(EchoGateway)