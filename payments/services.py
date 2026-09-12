"""Approval rules for vendor payment requests (Part B).

This module is PURE BUSINESS LOGIC: no Django models, no HTTP requests, no
database. Every function answers a question using only plain data (an amount,
role values, the approvals recorded so far).

Why separate it out (Separation of Concerns):
- Each rule can be unit-tested against the case-study numbers without spinning
  up a database or faking an HTTP request -- fast, focused tests.
- The exact same logic is reused wherever it's needed later (the approve/reject
  views, a serializer, a management command) instead of being copy-pasted into
  an HTTP handler.

Rules implemented so far:
  1. required_levels(amount) -> which approval tiers a payment needs.
"""

from decimal import Decimal

# --- Approval tiers -------------------------------------------------------
# The two tiers that can approve a payment. These string values are chosen to
# match payments.models.Profile's role constants (MANAGER, FINANCE), so a
# user's `profile.role` can be compared directly against a required tier when
# we wire this logic into the views later. They live here (not imported from
# the A-owned Profile model) so this rules layer stays importable and testable
# on its own; we reconcile them with Profile at view-wiring time.
MANAGER = "MANAGER"
FINANCE = "FINANCE"

# The case-study threshold: payments up to and including this need one manager;
# anything strictly above it also needs finance.
APPROVAL_THRESHOLD = Decimal("50000")


def required_levels(amount):
    """Return the approval tiers a payment of `amount` requires, in order.

    - amount <= 50,000  -> (MANAGER,)            one manager approval
    - amount  > 50,000  -> (MANAGER, FINANCE)    manager AND finance

    The amount is coerced to Decimal via str() so that floats like 50000.0 and
    strings like "67000" compare exactly, without binary-float rounding error
    (money must never be compared as a float).
    """
    amount = Decimal(str(amount))
    if amount <= APPROVAL_THRESHOLD:
        return (MANAGER,)
    return (MANAGER, FINANCE)
