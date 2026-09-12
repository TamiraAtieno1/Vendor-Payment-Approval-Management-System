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
  1. required_levels(amount)  -> which approval tiers a payment needs.
  2. can_approve(...)         -> may THIS user record an approval right now?
"""

from decimal import Decimal
from typing import NamedTuple, Optional

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


# --- Rule 2: may this user approve? ---------------------------------------
# Reason codes returned when an approval is NOT allowed. They are stable
# machine-readable strings the view layer can map to a clear HTTP 403 message,
# and they read plainly in tests.
REASON_NOT_AN_APPROVER = "not_an_approver"      # role is neither manager nor finance
REASON_SELF_APPROVAL = "self_approval"          # you created this request
REASON_TIER_NOT_REQUIRED = "tier_not_required"  # this amount doesn't need your tier
REASON_ALREADY_APPROVED = "already_approved"    # your tier already approved this request


class ApprovalCheck(NamedTuple):
    """Result of can_approve(). `reason` is None when allowed, else a REASON_* code.

    A NamedTuple (not a bare bool) so a caller gets both the yes/no AND why-not in
    one immutable, self-documenting value -- and can still read it as a boolean via
    `.allowed`.
    """

    allowed: bool
    reason: Optional[str]


def can_approve(*, approver_role, approver_is_requester, amount, approved_levels):
    """Decide whether `approver_role` may record an approval on this request now.

    All inputs are plain data, so this stays pure and testable:
      - approver_role:         the approver's Profile.role value.
      - approver_is_requester: True if the approver created this request.
      - amount:                the request amount (decides which tiers apply).
      - approved_levels:       tiers that have ALREADY approved (e.g. from
                               Approval rows), so a tier can't approve twice.

    Because our tier constants equal the Profile.role values, the approver's
    *tier* is simply their role (for MANAGER / FINANCE).

    Checks run coarse-to-fine; the FIRST failing one is reported:
      1. Must be an approver role at all            -> not_an_approver
      2. Separation of duties: not your own request -> self_approval
      3. This amount must actually need your tier   -> tier_not_required
      4. Your tier must not have approved already   -> already_approved
    """
    # 1. You must be a manager or finance to approve anything.
    if approver_role not in (MANAGER, FINANCE):
        return ApprovalCheck(False, REASON_NOT_AN_APPROVER)

    # 2. Separation of duties: the creator of a request can never approve it.
    if approver_is_requester:
        return ApprovalCheck(False, REASON_SELF_APPROVAL)

    # 3. Your tier must be one this amount actually requires (e.g. finance
    #    cannot stand in for the single manager a <=50k request needs).
    if approver_role not in required_levels(amount):
        return ApprovalCheck(False, REASON_TIER_NOT_REQUIRED)

    # 4. A given tier approves at most once per request.
    if approver_role in set(approved_levels):
        return ApprovalCheck(False, REASON_ALREADY_APPROVED)

    return ApprovalCheck(True, None)
