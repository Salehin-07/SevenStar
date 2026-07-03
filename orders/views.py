import json
import math
import time
import datetime
import logging
import threading
import requests
import stripe
import googlemaps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.email_utils import (
    build_booking_rows,
    send_templated_email,
    _row,
    _table,
    _body,
    _button,
    _greeting,
    _header,
    _info_box,
    _footer,
    _wrap,
    BG, SURFACE, GOLD, GOLD_LT, TEXT, MUTED, DARK, BORDER, FOOTER, FONT,
)

from .models import Discount, Order, Rates

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Service type configuration
# ─────────────────────────────────────────────────────────────────────────────

MELBOURNE_AIRPORT = "Melbourne Airport"

SERVICE_TYPES = {
    "ptp": {
        "label": "Point to Point",
        "show_destination": True,
        "show_flight": False,
        "lock_pickup": None,
        "lock_destination": None,
        "flat": False,
    },
    "oh": {
        "label": "Hourly / As Directed",
        "show_destination": False,
        "show_flight": False,
        "lock_pickup": None,
        "lock_destination": None,
        "flat": True,
    },
    "fair": {
        "label": "From Airport",
        "show_destination": True,
        "show_flight": True,
        "lock_pickup": MELBOURNE_AIRPORT,
        "lock_destination": None,
        "flat": False,
    },
    "tair": {
        "label": "To Airport",
        "show_destination": True,
        "show_flight": True,
        "lock_pickup": None,
        "lock_destination": MELBOURNE_AIRPORT,
        "flat": False,
    },
}

# oh is WhatsApp-routed — no Stripe, no price calculation
_WHATSAPP_SERVICE_TYPES = {"oh"}
_WHATSAPP_NUMBER = "61483841489"  # +61 483 841 489 in international format

# Cost per baby/child seat
BABY_SEAT_COST_PER_SEAT = 15.00


# ─────────────────────────────────────────────────────────────────────────────
# Notification emails (async, non-blocking)
# ─────────────────────────────────────────────────────────────────────────────

def _send_notifications_async(order):
    def _send():
        reference = str(order.id).zfill(6)
        svc_label = SERVICE_TYPES.get(order.service_type, {}).get("label", order.service_type.upper())
        show_destination = order.service_type not in _WHATSAPP_SERVICE_TYPES

        rows = build_booking_rows(order)

        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email:
            admin_html = (
                f"<div style='font-family:{FONT};max-width:600px;margin:auto;"
                f"background:{BG};border:1px solid {BORDER};border-radius:12px;overflow:hidden;'>"
                + _header("SevenStar Limo", "New Booking")
                + f"<div style='padding:36px 32px 16px;'>"
                + _table(*rows)
                + "</div>"
                + _footer()
                + "</div>"
            )
            try:
                send_mail(
                    subject=f"New Booking #{reference} — {order.passenger_name}",
                    message=f"New booking #{reference} from {order.passenger_name}.",
                    from_email=settings.SERVER_EMAIL,
                    recipient_list=[admin_email],
                    html_message=admin_html,
                    fail_silently=True,
                )
            except Exception as exc:
                logger.error("Failed admin notification for order #%s: %s", order.id, exc)

        if order.passenger_email:
            try:
                send_templated_email(
                    subject=f"Booking Enquiry Received — Reference #{reference}",
                    recipient_list=[order.passenger_email],
                    header_subtitle="Booking Enquiry Received",
                    greeting_name=order.passenger_name,
                    body_text="Thank you for choosing SevenStar. We have received your enquiry and our team will be in touch shortly to confirm details.",
                    rows=rows,
                    info_text=f"Save your reference number #{reference}. Our team will contact you to confirm your booking.",
                    info_highlight=f"#{reference}",
                )
            except Exception as exc:
                logger.error("Failed customer notification for order #%s: %s", order.id, exc)

    threading.Thread(target=_send, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# Email: payment request (admin-created order, unpaid)
# ─────────────────────────────────────────────────────────────────────────────

def _send_payment_request_email(order, request=None):
    reference = str(order.id).zfill(6)
    svc_label = SERVICE_TYPES.get(order.service_type, {}).get("label", order.service_type.upper())
    has_price = order.total_price is not None

    if request:
        payment_url = request.build_absolute_uri(reverse('pay', args=[order.id]))
    else:
        payment_url = reverse('pay', args=[order.id])

    rows = build_booking_rows(order)

    bank_info = ""
    try:
        from core.models import Contact
        contact = Contact.objects.first()
        if contact and contact.bank_details:
            bank_info = contact.bank_details
    except Exception:
        pass

    bank_section = ""
    if bank_info:
        bank_section = (
            f"<div style='margin-top:24px;padding:16px;background:{FOOTER};"
            f"border:1px solid {BORDER};border-radius:6px;'>"
            f"<p style='margin:0 0 8px;font-size:13px;font-weight:600;color:{DARK};'>"
            f"Bank Transfer Details</p>"
            f"<p style='margin:0;font-size:13px;color:{TEXT};line-height:1.6;white-space:pre-wrap;'>{bank_info}</p>"
            f"<p style='margin:8px 0 0;font-size:12px;color:{MUTED};'>"
            f"We encourage bank transfer to avoid processing fees. "
            f"Please use your reference number as the payment description.</p>"
            f"</div>"
        )

    pay_button = ""
    plain_msg = "Our team will be in touch shortly to confirm details."
    if has_price:
        pay_button = _button(payment_url, f"Pay Now — A${order.total_price}")
        plain_msg = f"Please pay A${order.total_price} to confirm your reservation:\n{payment_url}"

    body_html = (
        f"<div style='font-family:{FONT};max-width:600px;margin:auto;"
        f"background:{BG};border:1px solid {BORDER};border-radius:12px;overflow:hidden;'>"
        + _header("SevenStar Limo", "Payment Invoice")
        + f"<div style='padding:36px 32px 16px;'>"
        + _greeting(order.passenger_name)
        + _body("Thank you for choosing SevenStar. Your booking has been created and is awaiting payment to confirm your reservation.")
        + _table(*rows)
        + bank_section
        + pay_button
        + _info_box(f"Save your reference number #{reference}. Your booking will be confirmed once payment is received.", f"#{reference}")
        + "</div>"
        + _footer()
        + "</div>"
    )

    try:
        send_mail(
            subject=f"Payment Required — Booking #{reference}",
            message=(
                f"Dear {order.passenger_name},\n\n"
                f"Your booking has been created.\n"
                f"Reference: #{reference}\n"
                + plain_msg + "\n\n"
                f"Thank you for choosing SevenStar Limo & Chauffeur."
            ),
            from_email=settings.SERVER_EMAIL,
            recipient_list=[order.passenger_email],
            html_message=body_html,
            fail_silently=False,
        )
        logger.info("Payment request email sent for order #%s", order.id)
    except Exception as exc:
        logger.error("Failed to send payment request email for order #%s: %s", order.id, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Email: payment confirmed (admin-created order, now paid)
# ─────────────────────────────────────────────────────────────────────────────

def _send_payment_confirmed_email(order):
    reference = str(order.id).zfill(6)
    rows = build_booking_rows(order)

    try:
        send_templated_email(
            subject=f"Payment Confirmed — Booking #{reference}",
            recipient_list=[order.passenger_email],
            header_subtitle="Booking Confirmed",
            greeting_name=order.passenger_name,
            body_text="Thank you for your payment. Your booking has been confirmed and is now secured.",
            rows=rows,
            info_text=f"Save your reference number #{reference}. Your booking is fully confirmed.",
            info_highlight=f"#{reference}",
        )
        logger.info("Payment confirmed email sent for order #%s", order.id)
    except Exception as exc:
        logger.error("Failed to send payment confirmed email for order #%s: %s", order.id, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Email: admin notification when payment is received
# ─────────────────────────────────────────────────────────────────────────────

def _send_admin_payment_notification(order):
    reference = str(order.id).zfill(6)
    rows = build_booking_rows(order)

    admin_email = getattr(settings, 'ADMIN_EMAIL', None)
    if not admin_email:
        logger.warning("ADMIN_EMAIL not set — cannot send admin payment notification for order #%s", order.id)
        return

    admin_html = (
        f"<div style='font-family:{FONT};max-width:600px;margin:auto;"
        f"background:{BG};border:1px solid {BORDER};border-radius:12px;overflow:hidden;'>"
        + _header("SevenStar Limo", "Payment Received")
        + f"<div style='padding:36px 32px 16px;'>"
        + _table(*rows)
        + "</div>"
        + _footer()
        + "</div>"
    )

    try:
        send_mail(
            subject=f"Payment Received — Booking #{reference} — {order.passenger_name}",
            message=(
                f"Payment{f' of A${order.total_price}' if order.total_price else ''} "
                f"received for booking #{reference} "
                f"from {order.passenger_name}."
            ),
            from_email=settings.SERVER_EMAIL,
            recipient_list=[admin_email],
            html_message=admin_html,
            fail_silently=False,
        )
        logger.info("Admin payment notification sent for order #%s", order.id)
    except Exception as exc:
        logger.error("Failed to send admin payment notification for order #%s: %s", order.id, exc)


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_rates():
    qs = Rates.objects.all().order_by("base_price")
    if qs.exists():
        return [
            {
                "name":                     r.name,
                "img_url":                  r.img_url or "",
                "max_passengers":           r.max_passangers,
                "max_bags":                 r.max_bags,
                "base_price":               float(r.base_price),
                "per_km":                   float(r.per_km_rate),
                "stop":                     float(r.stop),
                "oh_rate":                  float(r.oh_rate),
                "remote_pickup_multiplier": float(r.remote_pickup_multiplier),
            }
            for r in qs
        ]
    return [
        {"name": "Sedan 1-5",    "max_passengers": 5,  "max_bags": 5,  "base_price": 30.00,  "per_km": 3.50, "stop": 15.00, "oh_rate": 100.00, "remote_pickup_multiplier": 1.0},
        {"name": "SUV 1-7",      "max_passengers": 7,  "max_bags": 7,  "base_price": 55.00,  "per_km": 5.50, "stop": 25.00, "oh_rate": 125.00, "remote_pickup_multiplier": 1.0},
        {"name": "Stretch 1-13", "max_passengers": 13, "max_bags": 13, "base_price": 135.00, "per_km": 9.50, "stop": 65.00, "oh_rate": 150.00, "remote_pickup_multiplier": 1.0},
    ]


def _get_discounts():
    disc = Discount.objects.first()
    if disc:
        return float(disc.th_discount), float(disc.return_discount)
    return 0.025, 0.05


def _find_rate(rates, vehicle_name):
    for r in rates:
        if r["name"] == vehicle_name:
            return r
    return rates[0]


# ─────────────────────────────────────────────────────────────────────────────
# Helper 1 – Distance (Google Maps Directions API)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_distance(pickup: str, destination: str, extra_stop: str | None) -> dict:
    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
    waypoints = [extra_stop] if extra_stop else None

    directions = gmaps.directions(
        origin=pickup,
        destination=destination,
        waypoints=waypoints,
        mode="driving",
        optimize_waypoints=False,
    )

    if not directions:
        raise ValueError("Google Maps returned no route for the given addresses.")

    total_meters = sum(leg["distance"]["value"] for leg in directions[0]["legs"])
    distance_km  = round(total_meters / 1000, 2)

    has_tolls = any(
        "toll" in step.get("html_instructions", "").lower()
        for leg in directions[0]["legs"]
        for step in leg["steps"]
    )

    return {
        "distance_km": distance_km,
        "has_tolls":   has_tolls,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper 2 – Remote pickup detection (Google Maps Geocoding API)
# ─────────────────────────────────────────────────────────────────────────────

# Melbourne CBD centroid
_MELB_CBD_LAT   = -37.8136
_MELB_CBD_LNG   = 144.9631
_REMOTE_RADIUS_KM = 10.0


def _is_remote_pickup(pickup_address: str) -> bool:
    try:
        gmaps   = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        results = gmaps.geocode(pickup_address)
        if not results:
            return False

        loc = results[0]["geometry"]["location"]
        lat, lng = loc["lat"], loc["lng"]

        R    = 6371.0
        dlat = math.radians(lat - _MELB_CBD_LAT)
        dlng = math.radians(lng - _MELB_CBD_LNG)
        a    = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(_MELB_CBD_LAT))
            * math.cos(math.radians(lat))
            * math.sin(dlng / 2) ** 2
        )
        distance_km = R * 2 * math.asin(math.sqrt(a))

        logger.debug(
            "Remote pickup check: '%s' → %.2f km from CBD (threshold %.1f km) → %s",
            pickup_address, distance_km, _REMOTE_RADIUS_KM,
            "REMOTE" if distance_km > _REMOTE_RADIUS_KM else "local",
        )
        return distance_km > _REMOTE_RADIUS_KM

    except Exception as exc:
        logger.warning("Remote pickup check failed for '%s': %s", pickup_address, exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Helper 3 – Pricing (fully DB-driven, per-km services only)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_price(
    service_type_key: str,
    distance_km:      float,
    has_tolls:        bool,
    vehicle:          str,
    extra_stop:       str | None,
    has_baby_seat:    bool,
    number_of_seats:  int,
    is_return_ride:   bool,
    pickup_time=None,
    pickup_address:   str = "",
) -> dict:

    rates                     = _get_rates()
    th_discount, ret_discount = _get_discounts()
    conf                      = _find_rate(rates, vehicle)

    # $15 per seat, minimum $15 if baby_seat checked but count is 0
    if has_baby_seat:
        seat_count = max(1, number_of_seats)
        baby_cost  = BABY_SEAT_COST_PER_SEAT * seat_count
    else:
        baby_cost = 0.00

    disc = Discount.objects.first()
    night_surcharge_rate = float(disc.extra_charge_for_down_hours) if disc else 0.30

    # ── Remote pickup multiplier ──────────────────────────────────────────────
    remote_mult = 1.0
    is_remote   = False
    if pickup_address and service_type_key not in ("oh",):
        raw_mult = conf.get("remote_pickup_multiplier", 1.0)
        if raw_mult != 1.0:
            is_remote   = _is_remote_pickup(pickup_address)
            remote_mult = raw_mult if is_remote else 1.0

    # ── Night surcharge ───────────────────────────────────────────────────────
    def _night_multiplier() -> float:
        if pickup_time is None:
            return 1.0
        try:
            hour = pickup_time.hour if hasattr(pickup_time, "hour") else int(str(pickup_time).split(":")[0])
            if hour < 6:
                return 1.0 + night_surcharge_rate
        except (AttributeError, ValueError):
            pass
        return 1.0

    def _apply_stripe(amount: float) -> float:
        return round(amount * 1.03, 2)

    night_mult = _night_multiplier()

    # ── Per-km services (ptp / fair / tair) ───────────────────────────────────
    base          = conf["base_price"]
    distance_cost = round(distance_km * conf["per_km"], 2)
    stop_cost     = conf["stop"] if extra_stop else 0.00
    toll_cost     = 18.50 if has_tolls else 0.00

    subtotal = round(base + distance_cost + stop_cost + toll_cost + baby_cost, 2)

    if is_return_ride:
        return_total    = round(subtotal * 2, 2)
        discount_amount = round(return_total * ret_discount, 2)
        pre_stripe      = round((return_total - discount_amount) * night_mult * remote_mult, 2)
        final_price     = _apply_stripe(pre_stripe)
        discount_label  = f"{round(ret_discount * 100, 2)}% return discount"
    else:
        discount_amount = 0.00
        final_price     = _apply_stripe(round(subtotal * night_mult * remote_mult, 2))
        discount_label  = ""

    if service_type_key in ["ptp", "fair", "tair"] and distance_km < 80 and final_price < 100.00:
        final_price = 100.00

    return {
        "service_type_key":         service_type_key,
        "base":                     base,
        "distance_km":              distance_km,
        "distance_cost":            distance_cost,
        "stop_cost":                stop_cost,
        "toll_cost":                toll_cost,
        "baby_cost":                baby_cost,
        "number_of_seats":          seat_count if has_baby_seat else 0,
        "subtotal_before_return":   subtotal,
        "return_multiplier":        is_return_ride,
        "return_discount":          discount_amount,
        "discount_label":           discount_label,
        "final_price":              final_price,
        "final_price_cents":        int(final_price * 100),
        "is_remote_pickup":         is_remote,
        "remote_pickup_multiplier": remote_mult,
    }


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp redirect builder (for hourly bookings)
# ─────────────────────────────────────────────────────────────────────────────

def _build_whatsapp_url(order, hours: str) -> str:
    reference = str(order.id).zfill(6)
    lines = [
        f"*New Hourly Hire Enquiry — #{reference}*",
        f"",
        f"*Name:* {order.passenger_name}",
        f"*Phone:* {order.passenger_number}",
        f"*Email:* {order.passenger_email}",
        f"",
        f"*Pickup:* {order.pickup_address}",
        f"*Date:* {order.pickup_date}",
        f"*Time:* {order.pickup_time}",
        f"*Hours Requested:* {hours}",
        f"*Vehicle:* {order.limo_service_type}",
        f"*Passengers:* {order.number_of_passengers}",
        f"*Bags:* {order.number_of_bags}",
    ]
    if order.baby_seat:
        lines.append(f"*Baby / Child Seats:* Yes")
    if order.number_of_babies:
        lines.append(f"*No. of Seats:* {order.number_of_babies}")
    if order.baby_ages:
        # Format each child's age individually
        ages_list = [a.strip() for a in order.baby_ages.split(",") if a.strip()]
        for i, age in enumerate(ages_list, 1):
            lines.append(f"*Child {i} Age:* {age}")
    if order.special_instruction:
        lines.append(f"*Instructions:* {order.special_instruction}")

    message = "\n".join(lines)
    import urllib.parse
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{_WHATSAPP_NUMBER}?text={encoded}"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers to parse per-child age fields from POST
# ─────────────────────────────────────────────────────────────────────────────

def _parse_child_ages(post_data, n_seats: int) -> str:
    """
    Reads child_age_1 … child_age_N from POST and returns a comma-separated
    string for storage in Order.baby_ages, e.g. "7 months,2 years,1 year".
    Ages are validated to be ≤ 10 years; blank entries stored as empty string.
    """
    ages = []
    for i in range(1, n_seats + 1):
        age = post_data.get(f"child_age_{i}", "").strip()
        ages.append(age)
    return ",".join(ages)


# ─────────────────────────────────────────────────────────────────────────────
# Booking view
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_type(request):
    raw = request.GET.get("type", request.POST.get("service_type_key", "ptp")).lower().strip()
    return raw if raw in SERVICE_TYPES else "ptp"


@login_required
def orders(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    type_key = _resolve_type(request)
    svc      = SERVICE_TYPES[type_key]
    rates    = _get_rates()

    is_hourly = type_key in _WHATSAPP_SERVICE_TYPES

    # ── POST ─────────────────────────────────────────────────────────────
    if request.method == "POST":
        action = request.POST.get("action", "calculate")

        pickup      = svc["lock_pickup"]      or request.POST.get("pickup_address", "").strip()
        destination = svc["lock_destination"] or request.POST.get("destination_address", "").strip()
        if is_hourly:
            destination = f"{svc['label']} — Open Route"

        extra_stop      = request.POST.get("additional_stop", "").strip() or None
        vehicle         = request.POST.get("limo_service_type", rates[0]["name"])
        has_baby_seat   = "baby_seat"   in request.POST
        is_return_ride  = "return_ride" in request.POST and not is_hourly
        flight_number   = request.POST.get("flight_number", "") if svc["show_flight"] else ""
        pickup_time_raw = request.POST.get("pickup_time", "").strip() or None
        hourly_hours    = request.POST.get("hourly_hours", "").strip() if is_hourly else ""

        # ── Baby/child seat details ───────────────────────────────────────
        n_seats       = 0
        baby_ages_raw = ""
        if has_baby_seat:
            try:
                n_seats = int(request.POST.get("number_of_babies", 0) or 0)
            except (ValueError, TypeError):
                n_seats = 0
            n_seats = max(0, min(4, n_seats))
            # Parse individual per-child age fields
            baby_ages_raw = _parse_child_ages(request.POST, n_seats)

        form_data = {
            "service_type_key":     type_key,
            "service_type_label":   svc["label"],
            "passenger_name":       request.POST.get("passenger_name", ""),
            "passenger_number":     request.POST.get("passenger_number", ""),
            "passenger_email":      request.POST.get("passenger_email", ""),
            "number_of_passengers": request.POST.get("number_of_passengers", 2),
            "number_of_bags":       request.POST.get("number_of_bags", 2),
            "pickup_address":       pickup,
            "destination_address":  destination,
            "additional_stop":      extra_stop or "",
            "flight_number":        flight_number,
            "pickup_date":          request.POST.get("pickup_date", str(datetime.date.today())),
            "pickup_time":          pickup_time_raw or "",
            "limo_service_type":    vehicle,
            "baby_seat":            has_baby_seat,
            "number_of_babies":     n_seats,
            # Pass individual ages back to template for re-population on error
            "baby_ages_list":       [a.strip() for a in baby_ages_raw.split(",")]
                                    if baby_ages_raw else [],
            "return_ride":          is_return_ride,
            "special_instruction":  request.POST.get("special_instruction", ""),
            "vehicle_colour":       request.POST.get("vehicle_colour", ""),
            "wedding_ribbon":       request.POST.get("wedding_ribbon", ""),
            "special_signboard":    request.POST.get("special_signboard", ""),
            "hourly_hours":         hourly_hours,
            "show_destination":     svc["show_destination"],
            "show_flight":          svc["show_flight"],
            "lock_pickup":          svc["lock_pickup"],
            "lock_destination":     svc["lock_destination"],
            "is_flat":              svc["flat"],
        }

        def form_error(msg):
            return render(request, "orders/booking_form.html", {
                "error": msg, "form_data": form_data, "svc": svc,
                "type_key": type_key, "rates": rates,
                "google_maps_key": settings.GOOGLE_MAPS_API_KEY,
                "is_hourly": is_hourly,
            })

        # ── Hourly: save order then redirect to WhatsApp ──────────────────
        if is_hourly:
            if not pickup:
                return form_error("Please enter your pickup address.")

            try:
                order = Order.objects.create(
                    user=request.user,
                    service_type=type_key,
                    passenger_name=form_data["passenger_name"],
                    passenger_number=form_data["passenger_number"],
                    passenger_email=form_data["passenger_email"],
                    number_of_passengers=form_data["number_of_passengers"],
                    number_of_bags=form_data["number_of_bags"],
                    pickup_address=pickup,
                    destination_address=destination,
                    additional_stop=extra_stop,
                    flight_number="",
                    pickup_date=form_data["pickup_date"],
                    pickup_time=pickup_time_raw or datetime.time(0, 0),
                    limo_service_type=vehicle,
                    baby_seat=has_baby_seat,
                    number_of_babies=n_seats,
                    baby_ages=baby_ages_raw,
                    return_ride=False,
                    special_instruction=form_data["special_instruction"],
                    vehicle_colour=form_data["vehicle_colour"],
                    wedding_ribbon=form_data["wedding_ribbon"],
                    special_signboard=form_data["special_signboard"],
                    hourly_hours=hourly_hours or None,
                    total_price=None,
                    paid=False,
                )
            except Exception as exc:
                return form_error(f"Could not save your enquiry: {exc}")

            _send_notifications_async(order)
            wa_url = _build_whatsapp_url(order, hourly_hours or "Not specified")
            return HttpResponseRedirect(wa_url)

        # ── Calculate (non-hourly) ────────────────────────────────────────
        if action == "calculate":
            try:
                if not pickup or not destination:
                    return form_error("Please enter both pickup and destination addresses.")
                route = calculate_distance(pickup, destination, extra_stop)

                breakdown = calculate_price(
                    service_type_key=type_key,
                    distance_km=route["distance_km"],
                    has_tolls=route["has_tolls"],
                    vehicle=vehicle,
                    extra_stop=extra_stop,
                    has_baby_seat=has_baby_seat,
                    number_of_seats=n_seats,
                    is_return_ride=is_return_ride,
                    pickup_time=pickup_time_raw,
                    pickup_address=pickup,
                )

                request.session["pending_price"]     = breakdown["final_price"]
                request.session["pending_breakdown"] = breakdown
                request.session["pending_has_tolls"] = route["has_tolls"]

                return render(request, "orders/booking_summary_preview.html", {
                    "form_data":   form_data,
                    "final_price": breakdown["final_price"],
                    "breakdown":   breakdown,
                    "has_tolls":   route["has_tolls"],
                    "svc":         svc,
                    "type_key":    type_key,
                    "rates":       rates,
                })

            except Exception as exc:
                return form_error(f"Route calculation failed: {exc}")

        # ── Confirm → Order → Stripe Checkout ─────────────────────────────
        elif action == "confirm":
            final_price = request.session.get("pending_price")
            if final_price is None:
                return form_error("Your session expired. Please recalculate the price.")

            try:
                order = Order.objects.create(
                    user=request.user,
                    service_type=type_key,
                    passenger_name=form_data["passenger_name"],
                    passenger_number=form_data["passenger_number"],
                    passenger_email=form_data["passenger_email"],
                    number_of_passengers=form_data["number_of_passengers"],
                    number_of_bags=form_data["number_of_bags"],
                    pickup_address=pickup,
                    destination_address=destination,
                    additional_stop=extra_stop,
                    flight_number=flight_number,
                    pickup_date=form_data["pickup_date"],
                    pickup_time=pickup_time_raw or datetime.time(0, 0),
                    limo_service_type=vehicle,
                    baby_seat=has_baby_seat,
                    number_of_babies=n_seats,
                    baby_ages=baby_ages_raw,
                    return_ride=is_return_ride,
                    special_instruction=form_data["special_instruction"],
                    vehicle_colour=form_data["vehicle_colour"],
                    wedding_ribbon=form_data["wedding_ribbon"],
                    special_signboard=form_data["special_signboard"],
                    hourly_hours=None,
                    total_price=final_price,
                    paid=False,
                )
            except Exception as exc:
                return form_error(f"Could not save your booking: {exc}")

            base_status_url = request.build_absolute_uri(reverse("status", args=[order.id]))
            success_url     = base_status_url + "?session_id={CHECKOUT_SESSION_ID}"
            cancel_url      = base_status_url

            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    mode="payment",
                    line_items=[{
                        "price_data": {
                            "currency": "aud",
                            "unit_amount": int(final_price * 100),
                            "product_data": {
                                "name": f"{svc['label']} — Melbourne Chauffeur",
                                "description": (
                                    f"{pickup} → {destination} on {form_data['pickup_date']}"
                                ),
                            },
                        },
                        "quantity": 1,
                    }],
                    customer_email=form_data["passenger_email"] or None,
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata={
                        "order_id":     order.id,
                        "service_type": type_key,
                        "passenger":    form_data["passenger_name"],
                        "pickup":       pickup,
                        "dropoff":      destination,
                        "pickup_date":  form_data["pickup_date"],
                    },
                )
                order.stripe_payment_intent_id = session.id
                order.save(update_fields=["stripe_payment_intent_id"])
                for k in ("pending_price", "pending_breakdown", "pending_has_tolls"):
                    request.session.pop(k, None)
                return HttpResponseRedirect(session.url)

            except stripe.error.StripeError as exc:
                order.delete()
                return form_error(f"Payment setup failed: {exc.user_message}")

    # ── GET ───────────────────────────────────────────────────────────────
    prefill_email = request.user.email or ""
    prefill_phone = ""
    try:
        prefill_phone = request.user.extended_profile.phone or ""
    except AttributeError:
        pass

    form_data = {
        "service_type_key":     type_key,
        "service_type_label":   svc["label"],
        "pickup_address":       svc["lock_pickup"]      or "",
        "destination_address":  svc["lock_destination"] or "",
        "pickup_date":          str(datetime.date.today()),
        "show_destination":     svc["show_destination"],
        "show_flight":          svc["show_flight"],
        "lock_pickup":          svc["lock_pickup"],
        "lock_destination":     svc["lock_destination"],
        "is_flat":              svc["flat"],
        "number_of_passengers": 2,
        "number_of_bags":       2,
        "number_of_babies":     0,
        "baby_ages_list":       [],
        "passenger_email":      prefill_email,
        "passenger_number":     prefill_phone,
        "limo_service_type":    rates[0]["name"],
    }
    return render(request, "orders/booking_form.html", {
        "form_data":       form_data,
        "svc":             svc,
        "type_key":        type_key,
        "rates":           rates,
        "google_maps_key": settings.GOOGLE_MAPS_API_KEY,
        "is_hourly":       is_hourly,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Pay for an existing order (public — no login required)
# ─────────────────────────────────────────────────────────────────────────────

def pay_for_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, paid=False)
    if order.total_price is None:
        return render(request, "orders/booking_cancelled.html", {
            "order": order,
            "no_price": True,
        })

    stripe.api_key = settings.STRIPE_SECRET_KEY
    base_url = request.build_absolute_uri(reverse("payment_status", args=[order.id]))
    success_url = base_url + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = base_url

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "aud",
                    "unit_amount": int(float(order.total_price) * 100),
                    "product_data": {
                        "name": f"{order.service_type_display} — Melbourne Chauffeur",
                        "description": f"{order.pickup_address} \u2192 {order.destination_address} on {order.pickup_date}",
                    },
                },
                "quantity": 1,
            }],
            customer_email=order.passenger_email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "order_id": order.id,
                "service_type": order.service_type,
                "passenger": order.passenger_name,
            },
        )
        order.stripe_payment_intent_id = session.id
        order.save(update_fields=["stripe_payment_intent_id"])
        return HttpResponseRedirect(session.url)
    except stripe.error.StripeError as exc:
        messages.error(request, f"Payment setup failed: {exc.user_message}")
        return redirect("orders")


# ─────────────────────────────────────────────────────────────────────────────
# Payment status (public — no login required)
# ─────────────────────────────────────────────────────────────────────────────

def payment_status(request, order_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    order = get_object_or_404(Order, id=order_id)

    session_id = request.GET.get("session_id")
    if session_id and not order.paid:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                updated = Order.objects.filter(id=order.id, paid=False).update(paid=True)
                order.refresh_from_db()
                if updated:
                    _send_payment_confirmed_email(order)
                    _send_admin_payment_notification(order)
        except stripe.error.StripeError as exc:
            logger.warning("Could not verify Stripe session %s: %s", session_id, exc)

    template = "orders/booking_confirmed.html" if order.paid else "orders/booking_cancelled.html"
    return render(request, template, {"order": order})


# ─────────────────────────────────────────────────────────────────────────────
# Order status
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def order_status(request, order_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    order = get_object_or_404(Order, id=order_id, user=request.user)

    session_id = request.GET.get("session_id")
    if session_id and not order.paid:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                updated = Order.objects.filter(id=order.id, paid=False).update(paid=True)
                order.refresh_from_db()
                if updated:
                    # Send payment confirmed notification for all paid bookings
                    _send_payment_confirmed_email(order)
                    _send_admin_payment_notification(order)
        except stripe.error.StripeError as exc:
            logger.warning("Could not verify Stripe session %s: %s", session_id, exc)

    template = "orders/booking_confirmed.html" if order.paid else "orders/booking_cancelled.html"
    return render(request, template, {"order": order})


# ─────────────────────────────────────────────────────────────────────────────
# Stripe webhook
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def stripe_webhook(request):
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        logger.warning("Stripe webhook signature failed: %s", exc)
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        if order_id and session.get("payment_status") == "paid":
            updated = Order.objects.filter(id=order_id, paid=False).update(paid=True)
            if updated:
                logger.info("Order #%s marked paid via webhook.", order_id)
                order_obj = Order.objects.filter(id=order_id).first()
                if order_obj:
                    _send_payment_confirmed_email(order_obj)
                    _send_admin_payment_notification(order_obj)

    elif event["type"] == "checkout.session.expired":
        order_id = event["data"]["object"].get("metadata", {}).get("order_id")
        if order_id:
            logger.warning("Checkout session expired for order #%s", order_id)

    return HttpResponse(status=200)


# ─────────────────────────────────────────────────────────────────────────────
# Finance dashboard
# ─────────────────────────────────────────────────────────────────────────────

TAB_CHOICES = [
    ("today",      "Today"),
    ("yesterday",  "Yesterday"),
    ("this_week",  "This Week"),
    ("prev_week",  "Prev Week"),
    ("this_month", "This Month"),
    ("prev_month", "Prev Month"),
    ("this_year",  "This Year"),
    ("prev_year",  "Prev Year"),
    ("lifetime",   "All Time"),
    ("custom",     "Custom"),
]

TAB_SEPARATORS = {"this_week", "this_month", "this_year", "lifetime", "custom"}


def _date_range_for_tab(tab, from_date=None, to_date=None):
    today = datetime.date.today()

    if tab == "today":
        return today, today
    elif tab == "yesterday":
        d = today - datetime.timedelta(days=1)
        return d, d
    elif tab == "this_week":
        mon = today - datetime.timedelta(days=today.weekday())
        return mon, mon + datetime.timedelta(days=6)
    elif tab == "prev_week":
        mon = today - datetime.timedelta(days=today.weekday() + 7)
        return mon, mon + datetime.timedelta(days=6)
    elif tab == "this_month":
        first = today.replace(day=1)
        if first.month == 12:
            last = first.replace(day=31)
        else:
            last = first.replace(month=first.month + 1, day=1) - datetime.timedelta(days=1)
        return first, last
    elif tab == "prev_month":
        first_this = today.replace(day=1)
        last_prev  = first_this - datetime.timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    elif tab == "this_year":
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    elif tab == "prev_year":
        y = today.year - 1
        return datetime.date(y, 1, 1), datetime.date(y, 12, 31)
    elif tab == "custom":
        return from_date, to_date
    else:  # lifetime
        return None, None


def _period_label(tab, from_date, to_date):
    MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    def fmt(d):
        if not d:
            return "—"
        return f"{d.day} {MONTHS[d.month - 1]} {d.year}"

    today = datetime.date.today()

    if tab == "today":
        return f"Today — {fmt(today)}"
    elif tab == "yesterday":
        return f"Yesterday — {fmt(today - datetime.timedelta(days=1))}"
    elif tab == "this_week":
        return f"This Week  {fmt(from_date)} → {fmt(to_date)}"
    elif tab == "prev_week":
        return f"Previous Week  {fmt(from_date)} → {fmt(to_date)}"
    elif tab == "this_month":
        return today.strftime("%B %Y")
    elif tab == "prev_month":
        d = today.replace(day=1) - datetime.timedelta(days=1)
        return d.strftime("%B %Y")
    elif tab == "this_year":
        return f"Year {today.year}"
    elif tab == "prev_year":
        return f"Year {today.year - 1}"
    elif tab == "lifetime":
        return "All Time"
    elif tab == "custom" and from_date and to_date:
        return f"{fmt(from_date)}  →  {fmt(to_date)}"
    return ""


def _build_context(request, tab, from_date, to_date, custom_from="", custom_to=""):
    if from_date and to_date:
        qs = Order.objects.filter(paid=True, pickup_date__range=(from_date, to_date))
    else:
        qs = Order.objects.filter(paid=True)

    orders = []
    total_earnings = total_cost = 0

    for o in qs.order_by("-pickup_date", "-created_at"):
        price  = float(o.total_price or 0)
        cost   = float(o.driver_fee  or 0)
        profit = price - cost
        total_earnings += price
        total_cost     += cost
        orders.append({
            "id":              o.pk,
            "passenger_name":  o.passenger_name  or "",
            "passenger_email": o.passenger_email or "",
            "service_type":    o.get_service_type_display(),
            "pickup_date":     str(o.pickup_date),
            "total_price":     price,
            "driver_fee":      cost,
            "profit":          profit,
        })

    total_profit = total_earnings - total_cost

    tabs = [
        {
            "key":       key,
            "label":     label,
            "active":    key == tab,
            "separator": key in TAB_SEPARATORS,
        }
        for key, label in TAB_CHOICES
    ]

    return {
        "orders":          orders,
        "tabs":            tabs,
        "active_tab":      tab,
        "period_label":    _period_label(tab, from_date, to_date),
        "custom_from":     custom_from,
        "custom_to":       custom_to,
        "total_earnings":  total_earnings,
        "total_cost":      total_cost,
        "total_profit":    total_profit,
        "order_count":     len(orders),
    }


@staff_member_required
def finances_view(request):
    today = datetime.date.today()
    mon   = today - datetime.timedelta(days=today.weekday())
    sun   = mon + datetime.timedelta(days=6)
    ctx   = _build_context(request, "this_week", mon, sun)
    return render(request, "orders/finances.html", ctx)


@staff_member_required
@require_POST
def finances_data(request):
    tab         = request.POST.get("tab", "this_week")
    custom_from = request.POST.get("custom_from", "").strip()
    custom_to   = request.POST.get("custom_to",   "").strip()

    from_date = to_date = None
    if tab == "custom":
        try:
            from_date = datetime.date.fromisoformat(custom_from)
            to_date   = datetime.date.fromisoformat(custom_to)
            if from_date > to_date:
                from_date, to_date = to_date, from_date
        except (ValueError, TypeError):
            tab = "this_week"

    from_date, to_date = _date_range_for_tab(tab, from_date, to_date)
    ctx = _build_context(request, tab, from_date, to_date, custom_from, custom_to)
    return render(request, "orders/finances.html", ctx)
