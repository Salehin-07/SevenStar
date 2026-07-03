import re
from django.http import HttpResponsePermanentRedirect
from django.conf import settings


class WwwRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if not settings.DEBUG and host == "sevenstarlimo.com.au":
            return HttpResponsePermanentRedirect(
                f"https://sevenstarlimo.com.au{request.get_full_path()}"
            )
        return self.get_response(request)
