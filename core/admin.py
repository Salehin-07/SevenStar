from django.contrib import admin
from .models import Contact, ContactRequest, FAQ

admin.site.register(Contact)
admin.site.register(ContactRequest)
admin.site.register(FAQ)