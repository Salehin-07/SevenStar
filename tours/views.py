import datetime
import json
import logging
import urllib.parse

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

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

from .models import TOUR_TYPE_CHOICES, TourBooking, TourCar

logger = logging.getLogger(__name__)

WHATSAPP_NUMBER = settings.WHATSAPP_NUMBER

# ─────────────────────────────────────────────────────────────────────────────
# Email helpers for tour bookings
# ─────────────────────────────────────────────────────────────────────────────

def _send_tour_notifications_async(booking):
    def _send():
        ref = str(booking.id).zfill(6)
        type_choices = dict(TOUR_TYPE_CHOICES)
        tour_label = type_choices.get(booking.tour_type, booking.tour_type.replace("_", " ").title())

        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email:
            rows = [
                _row("Reference", f"#{ref}"),
                _row("Tour", tour_label),
                _row("Name", booking.passenger_name),
                _row("Email", booking.passenger_email or "—"),
                _row("Phone", booking.passenger_number),
                _row("Pickup", booking.pickup_address),
                _row("Date", str(booking.booking_date)),
                _row("Time", str(booking.booking_time)[:5]),
            ]
            if booking.selected_car:
                rows.append(_row("Vehicle", str(booking.selected_car)))
            if booking.additional_stops:
                rows.append(_row("Stops", booking.additional_stops))
            if booking.special_instruction:
                rows.append(_row("Notes", booking.special_instruction))
            if booking.return_time:
                rows.append(_row("Return Time", str(booking.return_time)[:5]))

            html = (
                f"<div style='font-family:{FONT};max-width:600px;margin:auto;"
                f"background:{BG};border:1px solid {BORDER};border-radius:12px;overflow:hidden;'>"
                + _header("SevenStar Limo", "New Tour Inquiry")
                + f"<div style='padding:36px 32px 16px;'>"
                + _table(*rows)
                + "</div>"
                + _footer()
                + "</div>"
            )

            try:
                send_mail(
                    subject=f"New Tour Inquiry #{ref} — {booking.passenger_name}",
                    message=f"New tour inquiry #{ref} from {booking.passenger_name} for {tour_label}.",
                    from_email=settings.SERVER_EMAIL,
                    recipient_list=[admin_email],
                    html_message=html,
                    fail_silently=True,
                )
            except Exception as exc:
                logger.error("Failed admin tour notification #%s: %s", booking.id, exc)

        if booking.passenger_email:
            rows = [
                _row("Reference No.", f"#{ref}"),
                _row("Tour", tour_label),
                _row("Name", booking.passenger_name),
                _row("Pickup", booking.pickup_address),
                _row("Date", str(booking.booking_date)),
                _row("Time", str(booking.booking_time)[:5]),
            ]
            if booking.selected_car:
                rows.append(_row("Vehicle", str(booking.selected_car)))
            if booking.additional_stops:
                rows.append(_row("Stops", booking.additional_stops))

            try:
                send_templated_email(
                    subject=f"Tour Inquiry Received — Reference #{ref}",
                    recipient_list=[booking.passenger_email],
                    header_subtitle="Tour Inquiry Received",
                    greeting_name=booking.passenger_name,
                    body_text="Thank you for choosing SevenStar. We have received your tour inquiry and our team will be in touch shortly to confirm details.",
                    rows=rows,
                    info_text=f"Save your reference number #{ref}. Our team will contact you to confirm your booking.",
                    info_highlight=f"#{ref}",
                )
            except Exception as exc:
                logger.error("Failed customer tour notification #%s: %s", booking.id, exc)

    import threading
    threading.Thread(target=_send, daemon=True).start()


def _send_tour_payment_request_email(booking, request=None):
    ref = str(booking.id).zfill(6)
    type_choices = dict(TOUR_TYPE_CHOICES)
    tour_label = type_choices.get(booking.tour_type, booking.tour_type.replace("_", " ").title())
    has_price = booking.total_price is not None

    if request:
        payment_url = request.build_absolute_uri(reverse('tour_pay', args=[booking.id]))
    else:
        payment_url = reverse('tour_pay', args=[booking.id])

    rows = [
        _row("Reference No.", f"#{ref}"),
        _row("Tour", tour_label),
        _row("Name", booking.passenger_name),
        _row("Pickup", booking.pickup_address),
        _row("Date", str(booking.booking_date)),
        _row("Time", str(booking.booking_time)[:5]),
    ]
    if booking.selected_car:
        rows.append(_row("Vehicle", str(booking.selected_car)))
    if booking.additional_stops:
        rows.append(_row("Stops", booking.additional_stops))
    if has_price:
        rows.append(_row("Total Amount", f"A${booking.total_price}", highlight=True))

    # Get bank details from Contact model
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
        pay_button = _button(payment_url, f"Pay Now — A${booking.total_price}")
        plain_msg = f"Please pay A${booking.total_price} to confirm your tour booking:\n{payment_url}"

    body_html = (
        f"<div style='font-family:{FONT};max-width:600px;margin:auto;"
        f"background:{BG};border:1px solid {BORDER};border-radius:12px;overflow:hidden;'>"
        + _header("SevenStar Limo", "Tour Booking — Payment Required")
        + f"<div style='padding:36px 32px 16px;'>"
        + _greeting(booking.passenger_name)
        + _body("Thank you for choosing SevenStar. Your tour inquiry has been reviewed and is awaiting payment to confirm your reservation.")
        + _table(*rows)
        + bank_section
        + pay_button
        + _info_box(f"Save your reference number #{ref}. Your booking will be confirmed once payment is received.", f"#{ref}")
        + "</div>"
        + _footer()
        + "</div>"
    )

    try:
        send_mail(
            subject=f"Tour Payment Required — Reference #{ref}",
            message=(
                f"Dear {booking.passenger_name},\n\n"
                f"Your tour inquiry has been reviewed.\nReference: #{ref}\n"
                + plain_msg + "\n\n"
                f"Thank you for choosing SevenStar Limo & Chauffeur."
            ),
            from_email=settings.SERVER_EMAIL,
            recipient_list=[booking.passenger_email],
            html_message=body_html,
            fail_silently=False,
        )
        logger.info("Tour payment request email sent for #%s", booking.id)
    except Exception as exc:
        logger.error("Failed tour payment request email for #%s: %s", booking.id, exc)


def _send_tour_payment_confirmed_email(booking):
    ref = str(booking.id).zfill(6)
    type_choices = dict(TOUR_TYPE_CHOICES)
    tour_label = type_choices.get(booking.tour_type, booking.tour_type.replace("_", " ").title())

    rows = [
        _row("Reference No.", f"#{ref}"),
        _row("Tour", tour_label),
        _row("Name", booking.passenger_name),
        _row("Pickup", booking.pickup_address),
        _row("Date", str(booking.booking_date)),
        _row("Time", str(booking.booking_time)[:5]),
    ]
    if booking.selected_car:
        rows.append(_row("Vehicle", str(booking.selected_car)))
    if booking.total_price is not None:
        rows.append(_row("Amount Paid", f"A${booking.total_price}", highlight=True))

    try:
        send_templated_email(
            subject=f"Tour Payment Confirmed — Booking #{ref}",
            recipient_list=[booking.passenger_email],
            header_subtitle="Payment Confirmed",
            greeting_name=booking.passenger_name,
            body_text="Thank you for your payment. Your tour booking has been confirmed and is now secured.",
            rows=rows,
            info_text=f"Save your reference number #{ref}. Your tour is fully confirmed.",
            info_highlight=f"#{ref}",
        )
        logger.info("Tour payment confirmed email sent for #%s", booking.id)
    except Exception as exc:
        logger.error("Failed tour payment confirmed email for #%s: %s", booking.id, exc)


def _send_admin_tour_payment_notification(booking):
    ref = str(booking.id).zfill(6)
    type_choices = dict(TOUR_TYPE_CHOICES)
    tour_label = type_choices.get(booking.tour_type, booking.tour_type.replace("_", " ").title())

    admin_email = getattr(settings, 'ADMIN_EMAIL', None)
    if not admin_email:
        return

    rows = [
        _row("Reference", f"#{ref}"),
        _row("Tour", tour_label),
        _row("Name", booking.passenger_name),
        _row("Email", booking.passenger_email or "—"),
        _row("Phone", booking.passenger_number),
        _row("Pickup", booking.pickup_address),
        _row("Date", str(booking.booking_date)),
        _row("Time", str(booking.booking_time)[:5]),
    ]
    if booking.selected_car:
        rows.append(_row("Vehicle", str(booking.selected_car)))
    if booking.total_price is not None:
        rows.append(_row("Amount Paid", f"A${booking.total_price}", highlight=True))

    html = (
        f"<div style='font-family:{FONT};max-width:600px;margin:auto;"
        f"background:{BG};border:1px solid {BORDER};border-radius:12px;overflow:hidden;'>"
        + _header("SevenStar Limo", "Tour Payment Received")
        + f"<div style='padding:36px 32px 16px;'>"
        + _table(*rows)
        + "</div>"
        + _footer()
        + "</div>"
    )

    try:
        send_mail(
            subject=f"Tour Payment Received — #{ref} — {booking.passenger_name}",
            message=f"Payment{f' of A${booking.total_price}' if booking.total_price else ''} received for tour #{ref} from {booking.passenger_name}.",
            from_email=settings.SERVER_EMAIL,
            recipient_list=[admin_email],
            html_message=html,
            fail_silently=False,
        )
        logger.info("Admin tour payment notification sent for #%s", booking.id)
    except Exception as exc:
        logger.error("Failed admin tour payment notification for #%s: %s", booking.id, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Tour catalogue (static metadata — no prices)
# ─────────────────────────────────────────────────────────────────────────────

TOUR_CATALOGUE = {
    "yarra_valley": {
        "label":   "Yarra Valley Wine Tours",
        "emoji":   "🍷",
        "tagline": "Sip your way through Victoria's most celebrated wine country.",
        "about":   (
            "The Yarra Valley is home to more than 80 cellar doors set against dramatic "
            "mountain backdrops and lush green valleys. Famous for cool-climate Pinot Noir, "
            "Chardonnay, and world-class sparkling wines, it is just an hour from Melbourne CBD. "
            "Our knowledgeable drivers take you on a carefully curated route visiting boutique "
            "wineries, artisan producers, and gourmet providores at a relaxed, unhurried pace."
        ),
        "highlights": [
            "Tours through the Yarra Valley's best wineries.",
            "Stunning cool-climate wines and gourmet food.",
            "Friendly and knowledgeable winery tour drivers.",
            "Personalised, flexible service.",
            "Drinks and music of your choice.",
            "Intimate couples' tours and larger group packages.",
        ],
        "image": "img/tours/yarra_valley.jpg",
    },
    "mornington": {
        "label":   "Mornington Peninsula Wine Tours",
        "emoji":   "🌊",
        "tagline": "Ocean breezes, rolling vines, and exceptional Pinot — just 90 minutes from Melbourne.",
        "about":   (
            "The Mornington Peninsula is Victoria's most scenic wine destination, stretching "
            "between Port Phillip Bay and Western Port Bay. Celebrated for its maritime-influenced "
            "Pinot Noir and Chardonnay, the region also boasts artisan breweries, farm-gate "
            "producers, and stunning coastal lookouts."
        ),
        "highlights": [
            "Curated visits to the Peninsula's finest cellar doors.",
            "World-renowned Pinot Noir and Chardonnay tastings.",
            "Scenic coastal and hinterland routes.",
            "Expert local guides who know every hidden gem.",
            "Gourmet lunch stops at award-winning restaurants.",
            "Private and group tour options available.",
        ],
        "image": "img/tours/mornington.jpg",
    },
    "great_ocean_road": {
        "label":   "Great Ocean Road Tours",
        "emoji":   "🌊",
        "tagline": "One of the world's great coastal drives — experienced in complete luxury.",
        "about":   (
            "The Great Ocean Road is one of Australia's most iconic journeys, hugging the "
            "spectacular surf coast and passing through the Otway Ranges before revealing the "
            "breathtaking Twelve Apostles limestone stacks."
        ),
        "highlights": [
            "Private chauffeur-driven tours — no bus crowds.",
            "The iconic Twelve Apostles, Loch Ard Gorge, and London Arch.",
            "Otway Rainforest walks and Cape Otway Lighthouse.",
            "Flexible itinerary — stop wherever you choose.",
            "Koala and wildlife spotting en route.",
            "Full-day and sunrise/sunset tour options.",
        ],
        "image": "img/tours/great_ocean_road.jpg",
    },
    "golf": {
        "label":   "Golf Tours",
        "emoji":   "⛳",
        "tagline": "Play Victoria's finest courses — we handle the driving, you handle the birdies.",
        "about":   (
            "Victoria is home to some of Australia's most prestigious golf courses, from the "
            "Sandbelt's celebrated links to the spectacular clifftop fairways of the Mornington Peninsula."
        ),
        "highlights": [
            "Door-to-door transfers to Victoria's top golf courses.",
            "Ample luggage and golf bag storage in all vehicles.",
            "Multi-course day packages across the Melbourne Sandbelt.",
            "Corporate golf day coordination and group transport.",
            "Refreshments and music of your choice en route.",
            "Sunrise tee-time pickups — we're always on schedule.",
        ],
        "image": "img/tours/golf.jpg",
    },
    "melbourne_victorian": {
        "label":   "Melbourne and Victorian Tours",
        "emoji":   "🏙️",
        "tagline": "Discover the soul of Melbourne and Victoria's most extraordinary attractions.",
        "about":   (
            "From Melbourne's world-famous laneways, galleries, and food scene to the wider "
            "wonders of Victoria — the Dandenong Ranges, Phillip Island, Healesville Sanctuary."
        ),
        "highlights": [
            "Customised Melbourne city tours and hidden laneway experiences.",
            "Phillip Island penguin parade transfers and tours.",
            "Dandenong Ranges and Healesville Sanctuary day trips.",
            "Goldfields and historic town itineraries.",
            "Flexible half-day, full-day, and multi-day options.",
            "Expert local commentary throughout your journey.",
        ],
        "image": "img/tours/melbourne.jpg",
    },
    "grampians": {
        "label":   "Grampians Tours",
        "emoji":   "🏔️",
        "tagline": "Ancient sandstone ranges, Aboriginal rock art, and breathtaking panoramas.",
        "about":   (
            "The Grampians National Park is one of Victoria's most spectacular natural landscapes, "
            "featuring dramatic sandstone mountain ranges, stunning waterfalls, and abundant wildlife."
        ),
        "highlights": [
            "Private chauffeur transfers from Melbourne to the Grampians.",
            "MacKenzie Falls, Pinnacle Lookout, and Boroka Lookout.",
            "Aboriginal rock art sites with cultural context.",
            "Wildlife encounters — kangaroos, emus, and koalas.",
            "Grampians wineries and Halls Gap dining.",
            "Overnight and two-day itinerary packages available.",
        ],
        "image": "img/tours/grampians.jpg",
    },
    "peninsula_hot_springs": {
        "label":   "Peninsula Hot Springs Tours",
        "emoji":   "♨️",
        "tagline": "Soak, relax, and rejuvenate — arrive and depart in complete luxury.",
        "about":   (
            "Peninsula Hot Springs is Australia's premier bathing and spa destination, set across "
            "65 acres of natural thermal landscape on the Mornington Peninsula."
        ),
        "highlights": [
            "Return chauffeur transfers from Melbourne to Peninsula Hot Springs.",
            "Flexible departure times to suit your session booking.",
            "Combine with Mornington Peninsula wine tour on the same day.",
            "Comfortable, spacious vehicles perfect post-spa.",
            "Optional scenic coastal route through Frankston and Dromana.",
            "Group bookings and hen's party packages welcome.",
        ],
        "image": "img/tours/hot_springs.jpg",
    },
    "fruit_picking": {
        "label":   "Fruit Picking Tours",
        "emoji":   "🍓",
        "tagline": "From vine to basket — a fresh, family-friendly Victorian farm experience.",
        "about":   (
            "Victoria's fertile valleys and orchards produce some of Australia's finest stone "
            "fruits, berries, and tree fruits."
        ),
        "highlights": [
            "Family-friendly farm tours in Victoria's best fruit-growing regions.",
            "Seasonal availability — strawberries, cherries, apples, and berries.",
            "Yarra Valley and Wandin orchard visits.",
            "Combine with winery or distillery stops for adults.",
            "All ages welcome — great for school holidays.",
            "Relaxed, flexible pace with knowledgeable drivers.",
        ],
        "image": "img/tours/fruit_picking.jpg",
    },
    "victorian_ski": {
        "label":   "Victorian Ski Tours",
        "emoji":   "⛷️",
        "tagline": "Hit the slopes stress-free — we handle the alpine roads so you don't have to.",
        "about":   (
            "Victoria's alpine resorts — Mount Buller, Falls Creek, Mount Hotham, and Lake Mountain "
            "— offer spectacular skiing and snowboarding from June to September."
        ),
        "highlights": [
            "Transfers to Mount Buller, Falls Creek, Hotham, and Lake Mountain.",
            "Ample ski bag and equipment storage in every vehicle.",
            "Early morning departures to maximise your time on the snow.",
            "Return transfers — no driving tired alpine roads at night.",
            "Group bookings and family ski trip packages.",
            "Season pass holders and day-trippers equally welcome.",
        ],
        "image": "img/tours/ski.jpg",
    },
}

TOUR_LIST = [{"key": k, **v} for k, v in TOUR_CATALOGUE.items()]


# ─────────────────────────────────────────────────────────────────────────────
# API: return cars as JSON (for dynamic passenger cap)
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def tour_cars_api(request):
    cars = TourCar.objects.filter(is_active=True).values(
        "id", "name", "description", "max_passengers", "display_order"
    )
    data = []
    for c in cars:
        data.append({
            "id":             c["id"],
            "name":           c["name"],
            "description":    c["description"],
            "max_passengers": c["max_passengers"],
        })
    return JsonResponse({"cars": data})


# ─────────────────────────────────────────────────────────────────────────────
# Main booking view
# ─────────────────────────────────────────────────────────────────────────────


def tour_booking(request):
    valid_keys = {k for k, _ in TOUR_TYPE_CHOICES}
    raw_type   = request.GET.get("type", request.POST.get("tour_type", "")).lower().strip()

    if not raw_type or raw_type not in valid_keys:
        return render(request, "tours/tour_select.html", {"tours": TOUR_LIST})

    tour_key  = raw_type
    tour_info = TOUR_CATALOGUE[tour_key]
    cars      = list(TourCar.objects.filter(is_active=True).order_by("display_order", "name"))
    prefill_email = ""
    prefill_phone = ""
    if request.user.is_authenticated:
        prefill_email = request.user.email or ""
        try:
            prefill_phone = request.user.extended_profile.phone or ""
        except AttributeError:
            pass

    if request.method == "POST":
        passenger_name    = request.POST.get("passenger_name", "").strip()
        passenger_number  = request.POST.get("passenger_number", "").strip()
        passenger_email   = request.POST.get("passenger_email", "").strip()
        pickup_address    = request.POST.get("pickup_address", "").strip()
        booking_date_raw  = request.POST.get("booking_date", "").strip()
        booking_time_raw  = request.POST.get("booking_time", "").strip()
        return_time_raw   = request.POST.get("return_time", "").strip()
        num_passengers    = int(request.POST.get("number_of_passengers", 1))
        car_id            = request.POST.get("selected_car", "").strip()
        instructions      = request.POST.get("special_instruction", "").strip()

        raw_stops   = request.POST.getlist("stop[]")
        extra_stops = [s.strip() for s in raw_stops if s.strip()]
        stops_text  = "\n".join(extra_stops)

        def form_error(msg):
            return render(request, "tours/tour_booking_form.html", {
                "error":    msg,
                "tour_key": tour_key,
                "tour":     tour_info,
                "cars":     cars,
                "form_data": {
                    "passenger_name":       passenger_name,
                    "passenger_number":     passenger_number,
                    "passenger_email":      passenger_email,
                    "pickup_address":       pickup_address,
                    "booking_date":         booking_date_raw,
                    "booking_time":         booking_time_raw,
                    "return_time":          return_time_raw,
                    "number_of_passengers": num_passengers,
                    "selected_car":         car_id,
                    "special_instruction":  instructions,
                    "stops":                extra_stops,
                },
                "google_maps_key": settings.GOOGLE_MAPS_API_KEY,
            })

        if not passenger_name:
            return form_error("Please enter your full name.")
        if not passenger_number:
            return form_error("Please enter your phone number.")
        if not pickup_address:
            return form_error("Please enter your pickup address.")
        if not booking_date_raw:
            return form_error("Please select a tour date.")
        if not booking_time_raw:
            return form_error("Please select a pickup time.")

        selected_car_obj = None
        if car_id:
            try:
                selected_car_obj = TourCar.objects.get(id=car_id, is_active=True)
                if num_passengers > selected_car_obj.max_passengers:
                    return form_error(
                        f"The {selected_car_obj.name} seats a maximum of "
                        f"{selected_car_obj.max_passengers} passenger(s). "
                        f"Please select a larger vehicle or reduce passengers."
                    )
            except TourCar.DoesNotExist:
                return form_error("Invalid vehicle selected. Please choose from the list.")

        try:
            booking_date = datetime.date.fromisoformat(booking_date_raw)
        except ValueError:
            return form_error("Invalid date format.")

        try:
            h, m = booking_time_raw.split(":")
            booking_time = datetime.time(int(h), int(m))
        except (ValueError, AttributeError):
            booking_time = datetime.time(8, 0)

        return_time = None
        if return_time_raw:
            try:
                h, m = return_time_raw.split(":")
                return_time = datetime.time(int(h), int(m))
            except (ValueError, AttributeError):
                return_time = None

        try:
            booking = TourBooking.objects.create(
                user=request.user if request.user.is_authenticated else None,
                tour_type=tour_key,
                passenger_name=passenger_name,
                passenger_number=passenger_number,
                passenger_email=passenger_email,
                number_of_passengers=num_passengers,
                selected_car=selected_car_obj,
                pickup_address=pickup_address,
                additional_stops=stops_text,
                booking_date=booking_date,
                booking_time=booking_time,
                return_time=return_time,
                special_instruction=instructions or None,
            )
        except Exception as exc:
            return form_error(f"Could not save your inquiry: {exc}")

        _send_tour_notifications_async(booking)

        tour_label = tour_info["label"]
        car_name   = selected_car_obj.name if selected_car_obj else "Not specified"
        stops_line = ""
        if extra_stops:
            stops_formatted = "\n".join([f"  • {s}" for s in extra_stops])
            stops_line = f"\n📍 Additional Stops:\n{stops_formatted}"

        return_line = f"\n🔙 Return Time: {return_time_raw}" if return_time_raw else ""

        wa_message = (
            f"🌟 *SevenStar Limo — Tour Inquiry*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 Reference: #{str(booking.id).zfill(6)}\n"
            f"🗺️ Tour: {tour_label}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: {passenger_name}\n"
            f"📞 Phone: {passenger_number}\n"
        )
        if passenger_email:
            wa_message += f"✉️ Email: {passenger_email}\n"
        wa_message += (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚗 Vehicle: {car_name}\n"
            f"👥 Passengers: {num_passengers}\n"
            f"📍 Pickup: {pickup_address}"
            f"{stops_line}\n"
            f"📅 Date: {booking_date_raw}\n"
            f"⏰ Pickup Time: {booking_time_raw}"
            f"{return_line}\n"
        )
        if instructions:
            wa_message += f"📝 Notes: {instructions}\n"
        wa_message += "━━━━━━━━━━━━━━━━━━━━━\nI'd like to inquire about this tour. Please confirm availability."

        wa_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(wa_message)}"

        return render(request, "tours/tour_whatsapp_redirect.html", {
            "booking":   booking,
            "tour_info": tour_info,
            "wa_url":    wa_url,
        })

    # GET
    form_data = {
        "passenger_email":       prefill_email,
        "passenger_number":      prefill_phone,
        "booking_date":          str(datetime.date.today()),
        "number_of_passengers":  2,
    }

    return render(request, "tours/tour_booking_form.html", {
        "tour_key":        tour_key,
        "tour":            tour_info,
        "cars":            cars,
        "form_data":       form_data,
        "google_maps_key": settings.GOOGLE_MAPS_API_KEY,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Pay for an existing tour booking (public — no login required)
# ─────────────────────────────────────────────────────────────────────────────

def tour_pay(request, booking_id):
    booking = get_object_or_404(TourBooking, id=booking_id, paid=False)
    if booking.total_price is None:
        return render(request, "tours/tour_cancelled.html", {
            "booking": booking,
        })

    stripe.api_key = settings.STRIPE_SECRET_KEY
    base_url = request.build_absolute_uri(reverse("tour_payment_status", args=[booking.id]))
    success_url = base_url + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = base_url

    type_choices = dict(TOUR_TYPE_CHOICES)
    tour_label = type_choices.get(booking.tour_type, booking.tour_type.replace("_", " ").title())

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "aud",
                    "unit_amount": int(float(booking.total_price) * 100),
                    "product_data": {
                        "name": f"{tour_label} — SevenStar Limo",
                        "description": f"{booking.pickup_address} on {booking.booking_date}",
                    },
                },
                "quantity": 1,
            }],
            customer_email=booking.passenger_email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "booking_id":   booking.id,
                "tour_type":    booking.tour_type,
                "passenger":    booking.passenger_name,
            },
        )
        booking.stripe_payment_intent_id = session.id
        booking.save(update_fields=["stripe_payment_intent_id"])
        return HttpResponseRedirect(session.url)
    except stripe.error.StripeError as exc:
        messages.error(request, f"Payment setup failed: {exc.user_message}")
        return redirect("tours")


# ─────────────────────────────────────────────────────────────────────────────
# Payment status (public — no login required)
# ─────────────────────────────────────────────────────────────────────────────

def tour_payment_status(request, booking_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    booking = get_object_or_404(TourBooking, id=booking_id)

    session_id = request.GET.get("session_id")
    if session_id and not booking.paid:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                updated = TourBooking.objects.filter(id=booking.id, paid=False).update(paid=True)
                booking.refresh_from_db()
                if updated:
                    if booking.is_admin_booking:
                        _send_tour_payment_confirmed_email(booking)
                        _send_admin_tour_payment_notification(booking)
        except stripe.error.StripeError as exc:
            logger.warning("Could not verify Stripe session %s: %s", session_id, exc)

    if booking.paid:
        return render(request, "tours/tour_confirmed.html", {"booking": booking})
    return render(request, "tours/tour_cancelled.html", {"booking": booking})


# ─────────────────────────────────────────────────────────────────────────────
# Stripe webhook for tours
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def tour_stripe_webhook(request):
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        logger.warning("Tour webhook signature failed: %s", exc)
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        booking_id = session.get("metadata", {}).get("booking_id")
        if booking_id and session.get("payment_status") == "paid":
            updated = TourBooking.objects.filter(id=booking_id, paid=False).update(paid=True)
            if updated:
                logger.info("Tour booking #%s marked paid via webhook.", booking_id)
                booking_obj = TourBooking.objects.filter(id=booking_id).first()
                if booking_obj:
                    if booking_obj.is_admin_booking:
                        _send_tour_payment_confirmed_email(booking_obj)
                        _send_admin_tour_payment_notification(booking_obj)

    elif event["type"] == "checkout.session.expired":
        booking_id = event["data"]["object"].get("metadata", {}).get("booking_id")
        if booking_id:
            logger.warning("Tour checkout session expired for booking #%s", booking_id)

    return HttpResponse(status=200)


# ─────────────────────────────────────────────────────────────────────────────
# Status / confirmation views
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def tour_status(request, booking_id):
    booking   = get_object_or_404(TourBooking, id=booking_id, user=request.user)
    tour_info = TOUR_CATALOGUE.get(booking.tour_type, {})
    return render(request, "tours/tour_confirmed.html", {
        "booking":   booking,
        "tour_info": tour_info,
    })


@login_required
def tour_cancelled(request, booking_id):
    booking   = get_object_or_404(TourBooking, id=booking_id, user=request.user)
    tour_info = TOUR_CATALOGUE.get(booking.tour_type, {})
    return render(request, "tours/tour_cancelled.html", {
        "booking":   booking,
        "tour_info": tour_info,
    })
