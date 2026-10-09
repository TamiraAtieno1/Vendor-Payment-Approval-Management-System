from django.urls import path
from .views import health_check, EmployeeView

urlpatterns = [
    path('health/', health_check),
    path('employee/', EmployeeView.as_view(), name='employee-view'),
]