from django.contrib import admin
from django.http import HttpResponseRedirect
from .models import *
from .views import (
    _send_payment_request_email,
    _send_payment_confirmed_email,
    _send_admin_payment_notification,
)


# Register your models here.
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    fields = (
        "user",
        "service_type",
        "passenger_name",
        "passenger_number",
        "passenger_email",
        "number_of_passengers",
        "number_of_bags",
        "pickup_address",
        "destination_address",
        "additional_stop",
        "flight_number",
        "pickup_date",
        "pickup_time",
        "hourly_hours",
        "limo_service_type",
        "baby_seat",
        "number_of_babies",
        "baby_ages",
        "return_ride",
        "special_instruction",
        "vehicle_colour",
        "wedding_ribbon",
        "special_signboard",
        "total_price",
        "paid",
        "stripe_payment_intent_id",
        "driver_fee",
        "driver_name",
        "driver_number",
        "driver_email",
        "driver_address",
        "details_for_driver",
    )
    readonly_fields = ("is_admin_booking",)
    list_display = ("id", "passenger_name", "paid", "total_price", "pickup_date", "created_at")
    list_filter = ("paid", "service_type", "pickup_date")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_admin_booking = True
            super().save_model(request, obj, form, change)
            if obj.passenger_email:
                _send_payment_request_email(obj, request)
        else:
            original = Order.objects.get(pk=obj.pk)
            was_paid = original.paid
            super().save_model(request, obj, form, change)
            if not was_paid and obj.paid:
                _send_payment_confirmed_email(obj)
                _send_admin_payment_notification(obj)

    def response_change(self, request, obj):
        if "_send_payment_link" in request.POST:
            _send_payment_request_email(obj, request)
            self.message_user(request, "Payment link email sent to passenger.")
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)


admin.site.register(Discount)
admin.site.register(Rates)