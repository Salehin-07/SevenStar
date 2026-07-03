from django.urls import path
from . import views

urlpatterns = [
    path("",                           views.tour_booking,           name="tours"),
    path("status/<int:booking_id>/",   views.tour_status,            name="tour_status"),
    path("cancelled/<int:booking_id>/",views.tour_cancelled,         name="tour_cancelled"),
    path("api/cars/",                  views.tour_cars_api,          name="tour_cars_api"),
    path("pay/<int:booking_id>/",      views.tour_pay,               name="tour_pay"),
    path("payment-status/<int:booking_id>/", views.tour_payment_status, name="tour_payment_status"),
    path("stripe/webhook/",            views.tour_stripe_webhook,    name="tour_stripe_webhook"),
]
