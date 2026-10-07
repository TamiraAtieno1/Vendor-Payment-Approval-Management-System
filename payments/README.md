## Payment gateway integration

Payments go through a gateway **adapter** (`payments/gateways/`). Services talk
only to the `PaymentGateway` interface, never to a vendor directly, so multiple
providers can be used side by side.

### The adapter seam

| Module | Purpose |
| --- | --- |
| `base.py` | `PaymentGateway` ABC + `GatewayResult` (normalised charge outcome) |
| `mock.py` | `MockPaymentGateway` (`name = "mock"`) - deterministic test/dev provider |
| `registry.py` | `register()` / `get_gateway()` - resolves adapters by name |

The active gateway defaults to `PAYMENT_GATEWAY` in `imaraworks/settings.py`
(currently `'mock'`). Adding a real provider means writing one class:
`charge(*, amount, reference, idempotency_key) -> GatewayResult`, then calling
`register(MyGateway)`; nothing upstream changes.

### Mock vendor behaviour

- An amount or reference containing `FAIL` is **declined**; everything else is approved.
- The same `idempotency_key` always returns the identical result; never a double charge.

### Idempotency contract

`POST /api/payments/requests/<id>/pay/` (authenticated) charges an **approved**
request. The body is optional: `{"idempotency_key": "<client-supplied key>"}`.

- Clients supply a key so retries are safe (Stripe-style semantics). Without a
  key the service generates one, so only the caller can decide what is a retry.
- The key is stored **unique** on `PaymentTransaction`; replaying a key returns
  the original transaction (`"replayed": true`) and **never calls the gateway**.
- A request must be `APPROVED` (or `FAILED`, to retry); anything else returns 400.

### Payment request lifecycle

```
DRAFT -> PENDING -> APPROVED -> PAID     (successful charge)
              \-> REJECTED               (rejected during approval)
                          \-> FAILED     (declined; retryable with a new key)
```

### Setup

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python manage.py migrate
venv/bin/python manage.py seed_users   # users, vendors, projects, sample requests
venv/bin/python manage.py test         # 46 tests
```