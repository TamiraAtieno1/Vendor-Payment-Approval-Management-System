"""Unit tests for the pure approval rules (payments/services.py).

These use plain SimpleTestCase (no database) because the logic under test is
pure -- it touches no models. Numbers are taken straight from the case study so
the tests double as executable documentation of the business rules.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from payments import services
from payments.services import MANAGER, FINANCE


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
