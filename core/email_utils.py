from django.conf import settings
from django.core.mail import send_mail

BG      = "#faf8f3"
SURFACE = "#ffffff"
GOLD    = "#b8902e"
GOLD_LT = "#d4aa4a"
TEXT    = "#6b6560"
MUTED   = "#a09890"
DARK    = "#1a1714"
BORDER  = "#e8e2d6"
FOOTER  = "#f3efe6"
FONT    = "'Jost',Arial,sans-serif"


def _header(title, subtitle=None):
    sub = ""
    if subtitle:
        sub = f"<p style='margin:6px 0 0;font-size:13px;letter-spacing:2px;text-transform:uppercase;color:{GOLD_LT};'>{subtitle}</p>"
    return (
        f"<div style='background:{DARK};padding:28px 32px;"
        f"border-bottom:2px solid {GOLD};text-align:center;'>"
        f"<p style='margin:0;font-size:11px;letter-spacing:3px;text-transform:uppercase;"
        f"color:{GOLD_LT};font-weight:600;'>SevenStar Limo</p>"
        f"{sub}"
        f"</div>"
    )


def _greeting(name):
    return (
        f"<p style='margin:0 0 8px;font-size:14px;color:{TEXT};'>Dear {name},</p>"
    )


def _body(text):
    return (
        f"<p style='margin:0 0 28px;font-size:14px;color:{TEXT};line-height:1.7;'>{text}</p>"
    )


def _row(label, value, highlight=False):
    val_style = (
        f"padding:10px 8px;color:{'#1a1714' if highlight else TEXT};"
        f"{'font-size:16px;font-weight:700;' if highlight else 'font-size:14px;'}"
    )
    lbl_style = (
        f"padding:10px 8px;color:{DARK};width:42%;font-size:14px;font-weight:600;"
    )
    row_bg = "background:#f8f6f2;" if highlight else ""
    return (
        f"<tr style='border-bottom:1px solid {BORDER};{row_bg}'>"
        f"<td style='{lbl_style}'>{label}</td>"
        f"<td style='{val_style}'>{value}</td>"
        f"</tr>"
    )


def _table(*rows):
    return (
        f"<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        + "".join(rows)
        + "</table>"
    )


def _button(url, text):
    return (
        f"<div style='text-align:center;margin-top:32px;'>"
        f"<a href='{url}' "
        f"style='display:inline-block;padding:16px 48px;background:{GOLD};"
        f"color:#1a1714;text-decoration:none;border-radius:50px;"
        f"font-weight:700;font-size:18px;font-family:{FONT};"
        f"letter-spacing:0.5px;"
        f"box-shadow:0 4px 12px rgba(0,0,0,0.15);'>{text}</a>"
        f"</div>"
    )


def _info_box(text, highlight_text=None):
    extra = ""
    if highlight_text:
        extra = f"<strong style='color:{GOLD};'>{highlight_text}</strong>. "
    return (
        f"<div style='margin-top:24px;padding:16px;background:{FOOTER};"
        f"border-left:3px solid {GOLD};border-radius:6px;'>"
        f"<p style='margin:0;color:{MUTED};font-size:13px;line-height:1.6;'>"
        f"{extra}{text}</p></div>"
    )


def _footer():
    return (
        f"<div style='padding:16px 32px;border-top:1px solid {BORDER};"
        f"background:{FOOTER};text-align:center;'>"
        f"<p style='margin:0;font-size:11px;color:{MUTED};'>"
        f"&copy; SevenStar Chauffeur &amp; Limo Service &middot; Melbourne</p>"
        f"</div>"
    )


def _wrap(body_html):
    return (
        f"<div style='font-family:{FONT};max-width:600px;margin:0 auto;"
        f"background:{BG};border:1px solid {BORDER};border-radius:12px;"
        f"overflow:hidden;'>"
        + body_html
        + "</div>"
    )


def send_templated_email(
    subject,
    recipient_list,
    header_title="SevenStar Limo",
    header_subtitle=None,
    greeting_name=None,
    body_text=None,
    rows=None,
    button_url=None,
    button_text=None,
    info_text=None,
    info_highlight=None,
    from_email=None,
    reply_to=None,
):
    parts = [_header(header_title, header_subtitle)]

    if greeting_name:
        parts.append(f"<div style='padding:36px 32px 16px;'>{_greeting(greeting_name)}")
    else:
        parts.append("<div style='padding:36px 32px 16px;'>")

    if body_text:
        parts.append(_body(body_text))

    if rows:
        parts.append(_table(*rows))

    if button_url and button_text:
        parts.append(_button(button_url, button_text))

    if info_text or info_highlight:
        parts.append(_info_box(info_text, info_highlight))

    parts.append("</div>")
    parts.append(_footer())

    html_message = _wrap("".join(parts))

    plain_lines = []
    if greeting_name:
        plain_lines.append(f"Dear {greeting_name},")
        plain_lines.append("")
    if body_text:
        plain_lines.append(body_text.replace("<br>", "\n"))
    if rows:
        for r in rows:
            pass
    if button_url and button_text:
        plain_lines.append(f"{button_text}: {button_url}")
    if info_text:
        plain_lines.append(info_text)
    plain_lines.append("")
    plain_lines.append("— SevenStar Chauffeur & Limo Service")
    plain_message = "\n".join(plain_lines)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=from_email or settings.SERVER_EMAIL,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=False,
    )


def build_booking_rows(booking, price_label="Total Amount", price_field=None):
    """Build rows for any booking-like object that has common fields."""
    rows = []

    ref = str(getattr(booking, "id", "")).zfill(6)
    rows.append(_row("Reference No.", f"#{ref}"))

    service_type = getattr(booking, "service_type", None)
    if service_type:
        from orders.models import Order
        type_choices = dict(getattr(Order, "SERVICE_TYPE_CHOICES", []))
        label = type_choices.get(service_type, service_type.upper())
        rows.append(_row("Service", label))

    tour_type = getattr(booking, "tour_type", None)
    if tour_type:
        from tours.models import TOUR_TYPE_CHOICES
        type_choices = dict(TOUR_TYPE_CHOICES)
        label = type_choices.get(tour_type, tour_type.replace("_", " ").title())
        rows.append(_row("Tour Type", label))

    name = getattr(booking, "passenger_name", None)
    if name:
        rows.append(_row("Name", name))

    pickup = getattr(booking, "pickup_address", None)
    if pickup:
        rows.append(_row("Pickup Address", pickup))

    dest = getattr(booking, "destination_address", None)
    if dest:
        rows.append(_row("Destination", dest))

    stops = getattr(booking, "additional_stops", None) or getattr(booking, "additional_stop", None)
    if stops:
        rows.append(_row("Additional Stops", stops))

    pdate = getattr(booking, "pickup_date", None) or getattr(booking, "booking_date", None)
    if pdate:
        rows.append(_row("Date", str(pdate)))

    ptime = getattr(booking, "pickup_time", None) or getattr(booking, "booking_time", None)
    if ptime:
        rows.append(_row("Time", str(ptime)[:5]))

    vehicle = getattr(booking, "limo_service_type", None)
    if not vehicle:
        car = getattr(booking, "selected_car", None)
        if car:
            vehicle = str(car)
    if vehicle:
        rows.append(_row("Vehicle", vehicle))

    passengers = getattr(booking, "number_of_passengers", None)
    if passengers:
        rows.append(_row("Passengers", str(passengers)))

    flight = getattr(booking, "flight_number", None)
    if flight:
        rows.append(_row("Flight Number", flight))

    hours = getattr(booking, "hourly_hours", None)
    if hours:
        rows.append(_row("Hours Requested", f"{hours} hour(s)"))

    instructions = getattr(booking, "special_instruction", None)
    if instructions:
        rows.append(_row("Special Instructions", instructions))

    baby_seat = getattr(booking, "baby_seat", False)
    if baby_seat:
        rows.append(_row("Baby / Child Seats", "Yes"))
        n_babies = getattr(booking, "number_of_babies", 0)
        if n_babies:
            rows.append(_row("Number of Seats", str(n_babies)))
        baby_ages = getattr(booking, "baby_ages", "")
        if baby_ages:
            ages_display = ", ".join(
                f"Child {i+1}: {a.strip()}"
                for i, a in enumerate(baby_ages.split(","))
                if a.strip()
            )
            rows.append(_row("Ages of Children", ages_display))

    price_field_val = price_field
    if price_field_val is None:
        price_field_val = getattr(booking, "total_price", None)
    if price_field_val is not None:
        rows.append(_row(price_label, f"A${price_field_val}", highlight=True))

    return rows
