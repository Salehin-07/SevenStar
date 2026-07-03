from django.core.cache import cache
from .models import Contact

def context_processor(request):
    contact_info = cache.get('global_contact_info')
    if contact_info is None:
        try:
            contact_info = Contact.objects.first()
            if contact_info:
                cache.set('global_contact_info', contact_info, 86400) #24 hours
        except Exception:
            contact_info = None
            
    return {
        'contact': contact_info
    }
