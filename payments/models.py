from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    EMPLOYEE = 'EMPLOYEE'
    MANAGER = 'MANAGER'
    FINANCE = 'FINANCE'
    ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (EMPLOYEE, 'Employee'),
        (MANAGER, 'Manager'),
        (FINANCE, 'Finance Officer'),
        (ADMIN, 'Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class Vendor(models.Model):
    name = models.CharField(max_length=200, unique=True)
    service = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class PaymentRequest(models.Model):
    DRAFT = 'DRAFT'
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    PAID = 'PAID'
    FAILED = 'FAILED'

    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING, 'Pending Approval'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (PAID, 'Paid'),
        (FAILED, 'Failed'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vendor} - {self.amount} ({self.status})"


class PaymentTransaction(models.Model):
    INITIALIZED = 'INITIALIZED'
    PROCESSING = 'PROCESSING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'

    STATUS_CHOICES = [
        (INITIALIZED, 'Initialized'),
        (PROCESSING, 'Processing'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
    ]

    request = models.ForeignKey(
        PaymentRequest, on_delete=models.CASCADE, related_name='transactions'
    )
    gateway = models.CharField(max_length=50)
    idempotency_key = models.CharField(max_length=255, unique=True)
    external_ref = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=INITIALIZED
    )
    gateway_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.gateway} {self.idempotency_key} ({self.status})"