"""Gateway registry: maps adapter names to gateway classes.

Adapters for new providers register themselves with ``register`` and are then
reachable by name. ``get_gateway`` is the only entry point services use, so
nothing upstream needs to know which vendor is live.
"""
from django.conf import settings

from payments.gateways.base import PaymentGateway

_REGISTRY = {}


def register(gateway_cls):
    """Register a ``PaymentGateway`` subclass under its ``name``."""
    if not (isinstance(gateway_cls, type) and issubclass(gateway_cls, PaymentGateway)):
        raise TypeError(f"{gateway_cls} is not a PaymentGateway subclass")
    if gateway_cls.name in _REGISTRY:
        raise ValueError(f"gateway {gateway_cls.name!r} already registered")
    _REGISTRY[gateway_cls.name] = gateway_cls


def get_gateway(name=None) -> PaymentGateway:
    """Instantiate the gateway ``name`` (or the setting's default)."""
    name = name or getattr(settings, "PAYMENT_GATEWAY", "mock")
    if name not in _REGISTRY:
        raise ValueError(f"unknown payment gateway {name!r}")
    return _REGISTRY[name]()


# Built-in adapters.
from payments.gateways.mock import MockPaymentGateway  # noqa: E402

register(MockPaymentGateway)