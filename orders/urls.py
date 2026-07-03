from django.urls import path
from . import views
#app_name = 'orders'
urlpatterns = [
    path('', views.orders, name='orders'),
    path("pay/<int:order_id>/",             views.pay_for_order,   name="pay"),
    path("payment-status/<int:order_id>/",  views.payment_status,  name="payment_status"),
    path("status/<int:order_id>/",          views.order_status,    name="status"),
    path("stripe/webhook/",                 views.stripe_webhook,  name="stripe_webhook"),
    path("admin/finances/",                 views.finances_view,   name="finances"),
    path("admin/finances/data/",            views.finances_data,   name="finances_data"),
]
