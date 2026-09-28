from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.generic import TemplateView

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok'})

# Create your views here.
class EmployeeView(TemplateView):
    template_name = "payments/employee.html"

class ManagerView(TemplateView):
    template_name = "payments/manager.html"
