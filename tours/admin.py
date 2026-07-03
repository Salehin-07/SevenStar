from django.contrib import admin
from django.http import HttpResponseRedirect
from .models import TourCar, TourBooking
from .views import (
    _send_tour_payment_request_email,
    _send_tour_payment_confirmed_email,
    _send_admin_tour_payment_notification,
)


@admin.register(TourCar)
class TourCarAdmin(admin.ModelAdmin):
    list_display  = ['name', 'max_passengers', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active', 'max_passengers']
    ordering      = ['display_order', 'name']
    fields        = ['name', 'description', 'image', 'max_passengers', 'display_order', 'is_active']


@admin.register(TourBooking)
class TourBookingAdmin(admin.ModelAdmin):
    list_display  = ['id', 'passenger_name', 'tour_type', 'booking_date', 'selected_car', 'paid', 'total_price', 'created_at']
    list_filter   = ['tour_type', 'booking_date', 'paid', 'selected_car']
    search_fields = ['passenger_name', 'passenger_email', 'passenger_number', 'pickup_address']
    readonly_fields = ['created_at', 'is_admin_booking']
    raw_id_fields   = ['user', 'selected_car']
    actions = ['send_payment_link']

    fieldsets = (
        (None, {
            'fields': ('user', 'tour_type', 'passenger_name', 'passenger_number', 'passenger_email',
                       'number_of_passengers', 'selected_car', 'pickup_address', 'additional_stops',
                       'booking_date', 'booking_time', 'return_time', 'special_instruction')
        }),
        ('Payment', {
            'fields': ('total_price', 'paid', 'stripe_payment_intent_id', 'is_admin_booking'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_admin_booking = True
            super().save_model(request, obj, form, change)
            if obj.passenger_email:
                _send_tour_payment_request_email(obj, request)
        else:
            original = TourBooking.objects.get(pk=obj.pk)
            was_paid = original.paid
            super().save_model(request, obj, form, change)
            if not was_paid and obj.paid:
                _send_tour_payment_confirmed_email(obj)
                _send_admin_tour_payment_notification(obj)

    def response_change(self, request, obj):
        if "_send_payment_link" in request.POST:
            _send_tour_payment_request_email(obj, request)
            self.message_user(request, "Payment link email sent to passenger.")
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)

    def send_payment_link(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.passenger_email:
                _send_tour_payment_request_email(obj, request)
                count += 1
        self.message_user(request, f"Payment link email sent to {count} booking(s).")
    send_payment_link.short_description = "Send payment link email to selected bookings"
