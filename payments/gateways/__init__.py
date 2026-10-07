"""Payment gateway adapters (adapter pattern).

Every gateway that the system talks to implements the ``PaymentGateway``
interface. Services depend on the interface, never on a concrete vendor, so
swapping the mock for a real provider only means registering a new adapter.
"""
from payments.gateways.base import GatewayResult, PaymentGateway

__all__ = ["PaymentGateway", "GatewayResult"]