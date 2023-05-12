from django.contrib import admin
from .models import UserProfile, Order

# Register your models here.

admin.site.register(UserProfile)
admin.site.register(Order)
