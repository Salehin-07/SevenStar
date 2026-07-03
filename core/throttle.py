import time
from django.core.cache import cache
from django.http import HttpResponse
from django.urls import resolve


class AuthRateMiddleware:
    RATE = 10
    WINDOW = 60

    PROTECTED_NAMES = {"login", "signup", "verify_email"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            try:
                match = resolve(request.path_info)
            except Exception:
                return self.get_response(request)

            if match.url_name in self.PROTECTED_NAMES:
                ip = self._get_ip(request)
                key = f"throttle:{ip}:{match.url_name}"
                now = time.time()
                history = cache.get(key, [])
                history = [t for t in history if t > now - self.WINDOW]
                if len(history) >= self.RATE:
                    return HttpResponse(
                        "<h1>429 Too Many Requests</h1><p>Please wait before trying again.</p>",
                        status=429,
                    )
                history.append(now)
                cache.set(key, history, self.WINDOW)
        return self.get_response(request)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
