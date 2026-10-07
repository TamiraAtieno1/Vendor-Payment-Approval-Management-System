from django.urls import path
from .views import (
    PaymentRequestListCreateView,
    PaymentRequestPayView,
    health_check,
)

urlpatterns = [
    path('health/', health_check),
    path(
        'payments/requests/',
        PaymentRequestListCreateView.as_view(),
        name='payment-request-list',
    ),
    path(
        'payments/requests/<int:pk>/pay/',
        PaymentRequestPayView.as_view(),
        name='payment-request-pay',
    ),
]