from django.urls import path
from .views import RegisterView, LoginView, CreateOrderView, PayOrderView, RefundOrderView, ListOrderView, \
    GetUserBalanceView, UserDepositView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('order/create/', CreateOrderView.as_view(), name='create_order'),
    path('order/pay/', PayOrderView.as_view(), name='pay_order'),
    path('order/refund/', RefundOrderView.as_view(), name='refund_order'),
    path('order/list/', ListOrderView.as_view(), name='list_orders'),
    path('users/<int:user_id>/balance/', GetUserBalanceView.as_view(), name='get_user_balance'),
    path('users/<int:user_id>/deposit/', UserDepositView.as_view(), name='user_deposit'),
]
