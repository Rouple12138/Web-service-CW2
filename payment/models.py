from django.db import models
from django.contrib.auth.models import User
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)


class Order(models.Model):
    ORDER_TYPE_CHOICES = (
        ('order', 'Order'),
        ('refund_order', 'Refund Order'),
    )
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='from_orders', null=True)
    to_user_profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='to_orders')
    merchant_order_id = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False)
    stamp = models.UUIDField(default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='order')
    order_time = models.DateTimeField(auto_now_add=True)
    payment_time = models.DateTimeField(null=True, blank=True)
