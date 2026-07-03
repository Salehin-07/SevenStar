import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone


class Order(models.Model):
    SERVICE_TYPE_CHOICES = [
        ("ptp",  "Point to Point"),
        ("oh",   "Hourly / As Directed"),
        ("fair", "From Airport"),
        ("tair", "To Airport"),
    ]

    # Owner
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
    )

    # Service type
    service_type = models.CharField(max_length=10, choices=SERVICE_TYPE_CHOICES, default="ptp")

    # Passenger
    passenger_name   = models.CharField(max_length=200)
    passenger_number = models.CharField(max_length=30)
    passenger_email  = models.EmailField()

    # Trip
    number_of_passengers = models.IntegerField(default=2)
    number_of_bags       = models.IntegerField(default=2)
    pickup_address       = models.CharField(max_length=500)
    destination_address  = models.CharField(max_length=500)
    additional_stop      = models.CharField(max_length=500, null=True, blank=True)
    flight_number        = models.CharField(max_length=20, blank=True)
    pickup_date          = models.DateField(default=datetime.date.today)
    pickup_time          = models.TimeField(default=timezone.now)

    # Hourly hire — only populated for oh service type
    hourly_hours = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Number of hours requested (hourly hire only)"
    )

    # Vehicle
    limo_service_type   = models.CharField(max_length=50)
    baby_seat           = models.BooleanField(default=False)
    number_of_babies = models.IntegerField(default=0)
    baby_ages = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Comma-separated ages, e.g. '7 months,2 years,1 year'"
    )
    return_ride         = models.BooleanField(default=False)
    special_instruction = models.TextField(null=True, blank=True)
    vehicle_colour      = models.CharField(max_length=30, null=True, blank=True)
    wedding_ribbon      = models.CharField(max_length=30, null=True, blank=True)
    special_signboard   = models.CharField(max_length=200, blank=True)

    # Payment
    # total_price is nullable for hourly bookings — agent quotes manually via WhatsApp
    total_price  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid         = models.BooleanField(default=False)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    is_admin_booking = models.BooleanField(default=False)
    driver_fee   = models.DecimalField(max_digits=10, decimal_places=2,blank=True, default=20)
    driver_name    = models.CharField(max_length=100, blank=True, default='none')
    driver_number  = models.CharField(max_length=100, blank=True, default='none')
    driver_email   = models.CharField(max_length=100, blank=True, default='none')
    driver_address = models.CharField(max_length=200, blank=True, default='none')
    details_for_driver = models.CharField(max_length=500, blank=True, default='none')
    

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} [{self.service_type.upper()}] — {self.passenger_name} ({self.pickup_date})"

    @property
    def service_type_display(self):
        return dict(self.SERVICE_TYPE_CHOICES).get(self.service_type, self.service_type)


class Rates(models.Model):
    name           = models.CharField(max_length=100, default='Sedan 1-5')
    img_url        = models.URLField(null=True, blank=True)
    max_passangers = models.IntegerField(default=5)
    max_bags       = models.IntegerField(default=5)
    base_price     = models.DecimalField(max_digits=6, decimal_places=2, default=30)
    per_km_rate    = models.DecimalField(max_digits=6, decimal_places=2, default=3.50)
    stop           = models.DecimalField(max_digits=6, decimal_places=2, default=15)
    oh_rate        = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    remote_pickup_multiplier = models.DecimalField(
        max_digits=15, decimal_places=10, default=1.000,
        help_text="Applied when pickup is >10 km from Melbourne CBD. "
                  "E.g. 1.25 = 25% surcharge. Leave at 1.000 for no surcharge."
    )

    def __str__(self):
        return self.name


class Discount(models.Model):
    th_discount                 = models.DecimalField(max_digits=7, decimal_places=3, default=0.025)
    return_discount             = models.DecimalField(max_digits=7, decimal_places=3, default=0.05)
    extra_charge_for_down_hours = models.DecimalField(max_digits=7, decimal_places=3, default=0.3)

    def __str__(self):
        return "Manage Discounts & Extra Hour charge rates"
