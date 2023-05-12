from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import UserProfile, Order
from decimal import Decimal

# Create your tests here.
class SetUp(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.user_profile = UserProfile.objects.create(user=self.user, name='testname', balance=Decimal('100.00'))

        # 创建另一个用户和用户配置文件
        self.to_user = get_user_model().objects.create_user(username='touser', password='topassword')
        self.to_user_profile = UserProfile.objects.create(user=self.to_user, name='toname', balance=Decimal('100.00'))
        self.order = Order.objects.create(user_profile=self.user_profile, to_user_profile=self.to_user_profile, merchant_order_id='testmerchantorderid', price=Decimal('10.00'))

        # 登录并且get JWT token
        response = self.client.post('/payment/login/', {'ID': 'testuser', 'password': 'testpassword'})
        self.token = response.data['token']


# 这里是对于各接口的正确情况的测试
class RegisterViewTest(SetUp):
    def test_register_new_user(self):
        response = self.client.post('/payment/register/', {'name': 'testregister', 'email': 'testemail@test.com', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 200)


class LoginViewTest(SetUp):
    def test_login_existing_user(self):
        response = self.client.post('/payment/login/', {'ID': 'testuser', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 200)


class CreateOrderViewTest(SetUp):
    def test_create_order(self):
        # Add the token to the Authorization header
        response = self.client.post('/payment/order/create/', {'merchant_order_id': 'testmerchantorderid2', 'price': '20.00'}, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 200)


class PayOrderViewTest(SetUp):
    def test_pay_order(self):
        # Add the token to the Authorization header
        response = self.client.post('/payment/order/pay/', {'payment_id': self.order.payment_id}, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 200)


class RefundOrderViewTest(SetUp):
    def test_refund_order(self):
        # Add the token to the Authorization header
        response = self.client.post('/payment/order/refund/', {'payment_id': self.order.payment_id, 'price': '5.00'}, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 200)


class ListOrderViewTest(SetUp):
    def test_list_orders(self):
        # Add the token to the Authorization header
        response = self.client.get('/payment/order/list/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 200)


class GetUserBalanceViewTest(SetUp):
    def test_get_user_balance(self):
        # Add the token to the Authorization header
        response = self.client.get(f'/payment/users/{self.user.id}/balance/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['balance']), self.user_profile.balance)


class AddUserBalanceViewTest(SetUp):
    def test_add_user_balance(self):
        # Add the token to the Authorization header
        response = self.client.post(f'/payment/users/{self.user.id}/deposit/', {'amount': '50.00'}, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertEqual(str(self.user_profile.balance), '150.00')


# 下面是一些对于错误情况的测试
class LoginViewTestFail(SetUp):
    def test_login_non_existing_user(self):
        response = self.client.post('/payment/login/', {'ID': 'nonexistinguser', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 401)


class CreateOrderViewTestFail(SetUp):
    def test_create_order_with_negative_price(self):
        response = self.client.post('/payment/order/create/', {'merchant_order_id': 'testmerchantorderid2', 'price': '-20.00'}, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 400)


class PayOrderViewTestFail(SetUp):
    def test_pay_order_with_insufficient_balance(self):
        # Assume the balance is less than the order price
        self.user_profile.balance = Decimal('5.00')
        self.user_profile.save()
        response = self.client.post('/payment/order/pay/', {'payment_id': self.order.payment_id}, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 400)


class RefundOrderViewTestFail(SetUp):
    def test_refund_order_with_greater_price(self):
        response = self.client.post('/payment/order/refund/', {'payment_id': self.order.payment_id, 'price': '20.00'}, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 400)
