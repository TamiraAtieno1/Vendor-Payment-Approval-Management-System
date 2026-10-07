"""The gateway interface every payment provider adapter implements."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GatewayResult:
    """Normalised result returned by a gateway charge.

    Fields are plain data so services and callers stay decoupled from any
    vendor's response shape.
    """

    success: bool
    external_ref: str
    message: str = ""
    raw: dict = field(default_factory=dict)


class PaymentGateway(ABC):
    """Adapter interface for a payment provider.

    Subclasses set ``name`` (the identifier used by the registry and stored
    on ``PaymentTransaction.gateway``) and implement ``charge``.
    """

    name: str

    @abstractmethod
    def charge(self, *, amount, reference, idempotency_key) -> GatewayResult:
        """Attempt to charge ``amount`` for ``reference``.

        ``amount`` is a string/decimal in the system's currency. ``reference``
        is the application's id for the charge (transaction/receipt). The same
        ``idempotency_key`` must always produce the same result -- never a
        double charge.
        """
        raise NotImplementedError