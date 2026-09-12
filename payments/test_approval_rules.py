"""Unit tests for the pure approval rules (payments/services.py).

These use plain SimpleTestCase (no database) because the logic under test is
pure -- it touches no models. Numbers are taken straight from the case study so
the tests double as executable documentation of the business rules.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from payments import services
from payments.services import (
    MANAGER,
    FINANCE,
    REASON_NOT_AN_APPROVER,
    REASON_SELF_APPROVAL,
    REASON_TIER_NOT_REQUIRED,
    REASON_ALREADY_APPROVED,
)

EMPLOYEE = "EMPLOYEE"
ADMIN = "ADMIN"


class RequiredLevelsTests(SimpleTestCase):
    """Rule 1: tiering. <=50k needs a manager; >50k needs manager AND finance."""

    # --- Case-study amounts that stay at or below the threshold ---
    def test_24500_needs_one_manager(self):
        self.assertEqual(services.required_levels(24_500), (MANAGER,))

    def test_42000_needs_one_manager(self):
        self.assertEqual(services.required_levels(42_000), (MANAGER,))

    # --- Case-study amounts above the threshold ---
    def test_67000_needs_manager_and_finance(self):
        self.assertEqual(services.required_levels(67_000), (MANAGER, FINANCE))

    def test_148000_needs_manager_and_finance(self):
        self.assertEqual(services.required_levels(148_000), (MANAGER, FINANCE))

    # --- The boundary: exactly 50,000 is "<= 50,000", so one manager only ---
    def test_exactly_50000_needs_one_manager(self):
        self.assertEqual(services.required_levels(50_000), (MANAGER,))

    def test_just_over_50000_needs_finance_too(self):
        self.assertEqual(
            services.required_levels(Decimal("50000.01")), (MANAGER, FINANCE)
        )

    # --- Type-robustness: the rule must not depend on float quirks ---
    def test_accepts_decimal_and_string_amounts(self):
        self.assertEqual(services.required_levels(Decimal("24500")), (MANAGER,))
        self.assertEqual(services.required_levels("67000"), (MANAGER, FINANCE))


class CanApproveTests(SimpleTestCase):
    """Rule 2: may-this-user-approve (RBAC + self-approval + tier correctness)."""

    # --- The allowed paths ---
    def test_manager_approves_small_request_they_did_not_create(self):
        # carol (manager) approving a 24,500 request raised by alice.
        result = services.can_approve(
            approver_role=MANAGER,
            approver_is_requester=False,
            amount=24_500,
            approved_levels=[],
        )
        self.assertEqual(result, services.ApprovalCheck(True, None))
        self.assertTrue(result.allowed)

    def test_finance_may_approve_large_request_after_manager(self):
        # faith (finance) on a 67,000 request the manager already approved.
        result = services.can_approve(
            approver_role=FINANCE,
            approver_is_requester=False,
            amount=67_000,
            approved_levels=[MANAGER],
        )
        self.assertTrue(result.allowed)

    def test_finance_may_approve_large_request_before_manager(self):
        # The two >50k approvals are separate and order-independent.
        result = services.can_approve(
            approver_role=FINANCE,
            approver_is_requester=False,
            amount=148_000,
            approved_levels=[],
        )
        self.assertTrue(result.allowed)

    # --- RBAC: only manager / finance roles may approve ---
    def test_employee_cannot_approve(self):
        result = services.can_approve(
            approver_role=EMPLOYEE,
            approver_is_requester=False,
            amount=24_500,
            approved_levels=[],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, REASON_NOT_AN_APPROVER)

    def test_admin_cannot_approve(self):
        result = services.can_approve(
            approver_role=ADMIN,
            approver_is_requester=False,
            amount=24_500,
            approved_levels=[],
        )
        self.assertEqual(result.reason, REASON_NOT_AN_APPROVER)

    # --- Separation of duties: no approving your own request ---
    def test_manager_cannot_approve_own_request(self):
        result = services.can_approve(
            approver_role=MANAGER,
            approver_is_requester=True,
            amount=24_500,
            approved_levels=[],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, REASON_SELF_APPROVAL)

    # --- Tier correctness: your tier must be one the amount needs ---
    def test_finance_cannot_approve_manager_only_request(self):
        # 24,500 needs a manager only; a finance approval doesn't count.
        result = services.can_approve(
            approver_role=FINANCE,
            approver_is_requester=False,
            amount=24_500,
            approved_levels=[],
        )
        self.assertEqual(result.reason, REASON_TIER_NOT_REQUIRED)

    # --- No double-approval by the same tier ---
    def test_manager_cannot_approve_twice(self):
        result = services.can_approve(
            approver_role=MANAGER,
            approver_is_requester=False,
            amount=67_000,
            approved_levels=[MANAGER],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, REASON_ALREADY_APPROVED)

    # --- Ordering: role check precedes the self-approval check ---
    def test_employee_on_own_request_reports_role_first(self):
        # An employee who raised the request fails on role, not self-approval,
        # because an employee can never approve anything.
        result = services.can_approve(
            approver_role=EMPLOYEE,
            approver_is_requester=True,
            amount=24_500,
            approved_levels=[],
        )
        self.assertEqual(result.reason, REASON_NOT_AN_APPROVER)


class IsFullyApprovedTests(SimpleTestCase):
    """Rule 3: is-it-fully-approved (all required tiers have approved)."""

    def test_small_request_fully_approved_by_one_manager(self):
        self.assertTrue(services.is_fully_approved(24_500, [MANAGER]))

    def test_small_request_not_approved_with_no_approvals(self):
        self.assertFalse(services.is_fully_approved(24_500, []))

    def test_large_request_needs_both_tiers(self):
        self.assertFalse(services.is_fully_approved(67_000, [MANAGER]))
        self.assertFalse(services.is_fully_approved(67_000, [FINANCE]))
        self.assertTrue(services.is_fully_approved(67_000, [MANAGER, FINANCE]))

    def test_order_of_approvals_does_not_matter(self):
        self.assertTrue(services.is_fully_approved(148_000, [FINANCE, MANAGER]))

    def test_extra_approval_levels_are_tolerated(self):
        # A finance approval on a manager-only request doesn't block completion.
        self.assertTrue(services.is_fully_approved(24_500, [MANAGER, FINANCE]))
