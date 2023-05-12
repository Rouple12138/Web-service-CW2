from django.utils import timezone
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .models import Order, UserProfile
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterView(APIView):
    def post(self, request):
        name = request.data.get("name")
        email = request.data.get("email")
        password = request.data.get("password")
        User = get_user_model()

        # Check if the username or email has been taken
        if User.objects.filter(username=name).exists():
            return Response({"detail": "Username has been taken."}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({"detail": "Email has been taken."}, status=400)

        user = User.objects.create_user(username=name, email=email, password=password)

        # Create UserProfile for the new user
        UserProfile.objects.create(user=user)
        return Response({"accountID": user.id, "name": user.username})


class LoginView(APIView):
    def post(self, request):
        id = request.data.get("ID")
        password = request.data.get("password")
        user = authenticate(request, username=id, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({"token": str(refresh.access_token)})
        else:
            return Response({"detail": "Invalid ID/password."}, status=401)


class GetUserBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user_profile = UserProfile.objects.get(user__id=user_id)
            return Response({"balance": user_profile.balance})
        except UserProfile.DoesNotExist:
            return Response({"detail": "User profile not found."}, status=400)


class UserDepositView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            user_profile = UserProfile.objects.get(user__id=user_id)
            amount = Decimal(request.data.get('amount', '0.00'))
            user_profile.balance += amount
            user_profile.save()
            return Response({"balance": user_profile.balance})
        except UserProfile.DoesNotExist:
            return Response({"detail": "User profile not found."}, status=400)


class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        merchant_order_id = request.data.get("merchant_order_id")
        price = Decimal(request.data.get("price"))

        # Check if the price is positive
        if price <= 0:
            return Response({"detail": "Price must be positive."}, status=400)

        # Get the UserProfile for the authenticated user
        try:
            to_user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response({"detail": "User profile not found."}, status=400)

        # Create the order with to_user_profile, user_profile will be set when the order is paid
        order = Order.objects.create(to_user_profile=to_user_profile, merchant_order_id=merchant_order_id, price=price)

        # The payment_id is generated when the Order object is saved to the database
        payment_id = order.payment_id

        # The stamp is generated when the Order object is created
        stamp = order.stamp

        return Response({"payment_id": payment_id, "stamp": stamp})


class PayOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")

        # Get the Order object with the provided payment_id
        try:
            order = Order.objects.get(payment_id=payment_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=400)

        # Get the UserProfile for the authenticated user
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response({"detail": "User profile not found."}, status=400)

        # Set the user_profile of the order
        order.user_profile = user_profile

        # Check if the user has enough balance to pay for the order
        if user_profile.balance < order.price:
            return Response({"detail": "Insufficient balance."}, status=400)

        # Perform the payment operation as an atomic transaction
        with transaction.atomic():
            user_profile.balance -= order.price
            user_profile.save()
            order.to_user_profile.balance += order.price
            order.to_user_profile.save()
            order.payment_time = timezone.now()
            order.save()

        return Response({"stamp": order.stamp})


class RefundOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")
        refund_price = Decimal(request.data.get("price"))

        # Get the Order object with the provided payment_id
        try:
            order = Order.objects.get(payment_id=payment_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=400)

        # Check if the refund amount is less than or equal to the original order price
        if refund_price > order.price:
            return Response({"detail": "Refund amount is greater than original order price."}, status=400)

        # Check if the order has already been refunded
        if order.type == 'refund_order':
            return Response({"detail": "Order has already been refunded."}, status=400)

        # Check if the refunding user (to_user_profile) has enough balance for the refund
        if order.to_user_profile.balance < refund_price:
            return Response({"detail": "Insufficient balance for refund."}, status=400)

        # Perform the refund operation as an atomic transaction
        with transaction.atomic():
            order.user_profile.balance += refund_price
            order.user_profile.save()
            order.to_user_profile.balance -= refund_price
            order.to_user_profile.save()
            order.type = 'refund_order'
            order.save()

        return Response({
            'message': 'Refund successful',
            'from_user_balance': order.user_profile.balance,
            'to_user_balance': order.to_user_profile.balance
        }, status=200)


class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['merchant_order_id', 'price', 'payment_id', 'stamp', 'type', 'order_time', 'payment_time']


class ListOrderView(generics.ListAPIView):
    queryset = Order.objects.all().order_by('-payment_time')
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = UserProfile.objects.get(user=self.request.user)
        return Order.objects.filter(user_profile=user_profile).order_by('-payment_time')

