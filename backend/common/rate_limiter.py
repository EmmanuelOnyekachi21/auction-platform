from slowapi import Limiter
from slowapi.util import get_remote_address

from apps.authentication.jwt_service import decode_token
from config.settings import settings


def _get_key(request) -> str:
    """Rate limit key: user ID for authenticated requests, IP for anonymous.

    Extracts user ID directly from the JWT in the Authorization header
    without full validation — the dependency handles proper validation.
    Falls back to IP address for unauthenticated endpoints.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return get_remote_address(request)


# No global default_limits — only explicitly decorated endpoints are
# rate-limited. This avoids throttling health checks, webhooks, and
# public read endpoints unintentionally.
limiter = Limiter(
    key_func=_get_key,
    storage_uri=settings.redis_url,
)
