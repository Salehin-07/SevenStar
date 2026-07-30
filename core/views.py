from django.conf import settings
from django.shortcuts import render, redirect
from .models import ContactRequest, FAQ
from django.contrib import messages
from orders.models import Rates


def _get_home_rates():
    qs = Rates.objects.all().order_by("base_price")
    if qs.exists():
        return [
            {
                "name": r.name,
                "img_url": r.img_url or "",
                "max_passengers": r.max_passangers,
                "max_bags": r.max_bags,
                "base_price": float(r.base_price),
                "per_km": float(r.per_km_rate),
                "stop": float(r.stop),
                "oh_rate": float(r.oh_rate),
                "remote_pickup_multiplier": float(r.remote_pickup_multiplier),
            }
            for r in qs
        ]
    return []


def home(request):
    rates = _get_home_rates()
    faq = FAQ.objects.all()

    context = {
        'faq': faq,
        'google_maps_key': settings.GOOGLE_MAPS_API_KEY,
        'rates': rates,
        'type_key': 'ptp',
        'is_hourly': False,
        'form_data': {},
    }
    return render(request, 'core/index.html', context)


def contact(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        what_said = request.POST.get('what_said')
        
        try:
            contact_request = ContactRequest.objects.create(email=email, what_said=what_said)
            messages.success(request, "Thank you — we'll be in touch within the hour.")
            return redirect('contact')
            
        except Exception as e:
            messages.error(request, "Something went wrong. Please try again.")

        
    return render(request, 'core/contact.html')


def terms(request):
    return render(request, 'core/terms.html')

def about_us(request):
    return render(request, 'core/about.html')

def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')