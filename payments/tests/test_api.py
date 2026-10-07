from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from payments.models import PaymentRequest, PaymentTransaction, Vendor


class PaymentRequestApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dave", password="x")
        self.vendor = Vendor.objects.create(name="Acme", service="Cleaning")
        self.client.force_authenticate(self.user)

    def test_create_payment_request(self):
        response = self.client.post(
            reverse("payment-request-list"),
            {
                "vendor": self.vendor.id,
                "amount": "1250.00",
                "description": "Monthly cleaning",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request = PaymentRequest.objects.get(id=response.data["id"])
        self.assertEqual(request.status, PaymentRequest.DRAFT)
        self.assertEqual(request.created_by, self.user)
        self.assertEqual(request.amount, Decimal("1250.00"))

    def test_list_payment_requests(self):
        PaymentRequest.objects.create(
            vendor=self.vendor, amount=Decimal("10.00"), created_by=self.user
        )
        response = self.client.get(reverse("payment-request-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_missing_vendor_is_rejected(self):
        response = self.client.post(
            reverse("payment-request-list"),
            {"amount": "1250.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PayPaymentRequestApiTests(APITestCase):
    URL_NAME = "payment-request-pay"

    def setUp(self):
        self.user = User.objects.create_user(username="erin", password="x")
        self.vendor = Vendor.objects.create(name="Acme", service="Cleaning")
        self.approved = PaymentRequest.objects.create(
            vendor=self.vendor,
            amount=Decimal("500.00"),
            status=PaymentRequest.APPROVED,
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def test_pay_approved_request(self):
        url = reverse(self.URL_NAME, args=[self.approved.id])
        response = self.client.post(url, {"idempotency_key": "api-1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], PaymentTransaction.SUCCESS)
        self.assertFalse(response.data["replayed"])
        self.approved.refresh_from_db()
        self.assertEqual(self.approved.status, PaymentRequest.PAID)

    def test_pay_without_key_generates_one(self):
        url = reverse(self.URL_NAME, args=[self.approved.id])
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["idempotency_key"])

    def test_replay_returns_identical_payload(self):
        url = reverse(self.URL_NAME, args=[self.approved.id])
        self.client.post(url, {"idempotency_key": "same-1"})
        replay = self.client.post(url, {"idempotency_key": "same-1"})

        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(
            PaymentTransaction.objects.filter(request=self.approved).count(), 1
        )

    def test_unknown_request_returns_404(self):
        url = reverse(self.URL_NAME, args=[9999])
        response = self.client.post(url, {"idempotency_key": "k"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_approved_request_is_rejected(self):
        draft = PaymentRequest.objects.create(
            vendor=self.vendor,
            amount=Decimal("5.00"),
            status=PaymentRequest.DRAFT,
            created_by=self.user,
        )
        url = reverse(self.URL_NAME, args=[draft.id])
        response = self.client.post(url, {"idempotency_key": "k"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_pay_is_forbidden(self):
        self.client.force_authenticate(user=None)
        url = reverse(self.URL_NAME, args=[self.approved.id])
        response = self.client.post(url, {"idempotency_key": "k"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)