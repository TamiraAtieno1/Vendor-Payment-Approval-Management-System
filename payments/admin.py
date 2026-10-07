from django.contrib import admin
from .models import PaymentRequest, PaymentTransaction, Profile, Vendor, Project

# Register your models here.
admin.site.register(Profile)
admin.site.register(Vendor)
admin.site.register(Project)
admin.site.register(PaymentRequest)
admin.site.register(PaymentTransaction)