# campuscare/appointments/middleware.py — Step 5
from appointments.services import expire_stale_tokens


class TokenExpiryMiddleware:
    """Expire outdated tokens on the way into each request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        expire_stale_tokens()
        return self.get_response(request)
