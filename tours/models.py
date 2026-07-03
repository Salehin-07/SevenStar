import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone


TOUR_TYPE_CHOICES = [
    ("yarra_valley",        "Yarra Valley Winery Tours"),
    ("mornington",          "Mornington Peninsula Wine Tours"),
    ("great_ocean_road",    "Great Ocean Road Tours"),
    ("golf",                "Golf Tours"),
    ("melbourne_victorian", "Melbourne and Victorian Tours"),
    ("grampians",           "Grampians Tours"),
    ("peninsula_hot_springs", "Peninsula Hot Springs Tours"),
    ("fruit_picking",       "Fruit Picking Tours"),
    ("victorian_ski",       "Victorian Ski Tours"),
]


class TourCar(models.Model):
    name               = models.CharField(max_length=120, help_text="e.g. Mercedes S-Class")
    description        = models.CharField(max_length=255, blank=True, help_text="Short tagline shown on the card")
    image              = models.URLField(blank=True, null=True)
    max_passengers     = models.PositiveSmallIntegerField(default=4, help_text="Maximum passengers this vehicle seats")
    display_order      = models.PositiveSmallIntegerField(default=0, help_text="Lower = shown first")
    is_active          = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Tour Vehicle"
        verbose_name_plural = "Tour Vehicles"

    def __str__(self):
        return f"{self.name} (max {self.max_passengers} pax)"

    @property
    def image_url(self):
        if self.image:
            return self.image
        return None


class TourBooking(models.Model):
    user                  = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="tour_bookings")
    tour_type             = models.CharField(max_length=60)
    passenger_name        = models.CharField(max_length=180)
    passenger_number      = models.CharField(max_length=40)
    passenger_email       = models.EmailField(blank=True, null=True)              # already optional in DB
    number_of_passengers  = models.PositiveSmallIntegerField(default=1)
    selected_car          = models.ForeignKey(
        TourCar, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="bookings",
    )
    pickup_address        = models.CharField(max_length=300)
    additional_stops      = models.TextField(blank=True)
    booking_date          = models.DateField()
    booking_time          = models.TimeField()
    return_time           = models.TimeField(null=True, blank=True)    
    special_instruction   = models.TextField(blank=True, null=True)
    total_price           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid                  = models.BooleanField(default=False)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    is_admin_booking      = models.BooleanField(default=False)
    created_at            = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tour Inquiry"
        verbose_name_plural = "Tour Inquiries"

    def __str__(self):
        return f"#{str(self.id).zfill(6)} — {self.passenger_name}"