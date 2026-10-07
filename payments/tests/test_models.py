from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from payments.models import PaymentRequest, PaymentTransaction, Profile, Project, Vendor


class PaymentRequestModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="x")
        self.vendor = Vendor.objects.create(name="Acme", service="Cleaning")
        self.project = Project.objects.create(name="HQ Refurb")

    def _make(self, **kwargs):
        defaults = {
            "vendor": self.vendor,
            "project": self.project,
            "amount": Decimal("1000.00"),
            "description": "Cleaning services",
            "created_by": self.user,
        }
        defaults.update(kwargs)
        return PaymentRequest.objects.create(**defaults)

    def test_defaults_to_draft_status(self):
        request = self._make()
        self.assertEqual(request.status, PaymentRequest.DRAFT)

    def test_status_choices_cover_approval_and_payment_lifecycle(self):
        values = {c[0] for c in PaymentRequest.STATUS_CHOICES}
        self.assertEqual(
            values,
            {"DRAFT", "PENDING", "APPROVED", "REJECTED", "PAID", "FAILED"},
        )

    def test_amount_is_decimal_and_keeps_precision(self):
        request = self._make(amount=Decimal("50000.01"))
        request.refresh_from_db()
        self.assertEqual(request.amount, Decimal("50000.01"))
        self.assertNotIsInstance(request.amount, float)

    def test_invalid_status_rejected(self):
        request = self._make()
        request.status = "NOT_A_STATUS"
        with self.assertRaises(ValidationError):
            request.full_clean()

    def test_requires_vendor_and_creator(self):
        with self.assertRaises(IntegrityError):
            PaymentRequest.objects.create(amount=Decimal("1.00"))

    def test_str_includes_vendor_and_amount(self):
        request = self._make()
        self.assertIn("Acme", str(request))
        self.assertIn("1000", str(request))


class PaymentTransactionModelTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="bob", password="x")
        vendor = Vendor.objects.create(name="Acme", service="Cleaning")
        self.request = PaymentRequest.objects.create(
            vendor=vendor, amount=Decimal("100.00"), created_by=user
        )

    def _make(self, **kwargs):
        defaults = {
            "request": self.request,
            "gateway": "mock",
            "idempotency_key": "key-1",
            "amount": Decimal("100.00"),
        }
        defaults.update(kwargs)
        return PaymentTransaction.objects.create(**defaults)

    def test_defaults_to_initialized_status(self):
        txn = self._make()
        self.assertEqual(txn.status, PaymentTransaction.INITIALIZED)

    def test_status_choices(self):
        values = {c[0] for c in PaymentTransaction.STATUS_CHOICES}
        self.assertEqual(
            values, {"INITIALIZED", "PROCESSING", "SUCCESS", "FAILED"}
        )

    def test_idempotency_key_is_unique(self):
        self._make(idempotency_key="dup-key")
        with self.assertRaises(IntegrityError):
            PaymentTransaction.objects.create(
                request=self.request,
                gateway="mock",
                idempotency_key="dup-key",
                amount=Decimal("100.00"),
            )

    def test_gateway_response_defaults_to_null(self):
        txn = self._make()
        self.assertIsNone(txn.gateway_response)

    def test_external_ref_blank_until_gateway_responds(self):
        txn = self._make()
        self.assertEqual(txn.external_ref, "")

    def test_request_related_name_is_transactions(self):
        self._make()
        self.assertEqual(self.request.transactions.count(), 1)
