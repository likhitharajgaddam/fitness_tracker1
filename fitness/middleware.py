from http.cookies import Morsel
from urllib.parse import unquote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone
from django.utils.cache import add_never_cache_headers, patch_vary_headers

# Enable the CHIPS "Partitioned" cookie attribute on Python < 3.14 so
# browsers allow session & CSRF cookies inside cross-site HTTPS iframes.
if "partitioned" not in Morsel._reserved:
    Morsel._reserved["partitioned"] = "Partitioned"
if hasattr(Morsel, "_flags") and "partitioned" not in Morsel._flags:
    Morsel._flags = frozenset(Morsel._flags) | {"partitioned"}

_LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "testserver", "[::1]"}
_NO_CACHE_PREFIXES = (
    "/dashboard",
    "/goals",
    "/workouts",
    "/rewards",
    "/analytics",
    "/profile",
    "/settings",
    "/api/",
    "/login",
    "/signup",
    "/logout",
    "/challenge",
    "/tutorial",
)


def _is_external_https_request(request) -> bool:
    """
    Detect whether this request originated from an external HTTPS client
    (including behind Cloud Run + local nginx, where nginx listens on HTTP :8080
    and overwrites X-Forwarded-Proto with 'http' while preserving the real
    HTTPS hostname in X-Forwarded-Host).
    """
    forwarded_proto = (
        request.META.get("HTTP_X_FORWARDED_PROTO", "")
        .split(",")[0]
        .strip()
        .lower()
    )
    if request.is_secure() or forwarded_proto == "https":
        return True

    origin = (request.META.get("HTTP_ORIGIN") or "").strip().lower()
    referer = (request.META.get("HTTP_REFERER") or "").strip().lower()
    if origin.startswith("https://") or referer.startswith("https://"):
        return True

    forwarded_host = (
        request.META.get("HTTP_X_FORWARDED_HOST", "")
        .split(",")[0]
        .strip()
        .lower()
    )
    if forwarded_host:
        hostname = forwarded_host.split(":")[0]
        if hostname and hostname not in _LOCAL_HOSTNAMES:
            return True

    raw_host = (request.META.get("HTTP_HOST") or "").split(":")[0].strip().lower()
    if (
        getattr(settings, "APP_URL", "").startswith("https://")
        and raw_host
        and raw_host not in _LOCAL_HOSTNAMES
    ):
        return True

    return False


def _activate_request_timezone(request) -> bool:
    """Activate validated browser IANA timezone from cookie if present."""
    raw_tz = request.COOKIES.get("fittrack_tz")
    if not raw_tz:
        return False
    tz_name = unquote(raw_tz).strip()
    if not tz_name or len(tz_name) > 64:
        return False
    try:
        timezone.activate(ZoneInfo(tz_name))
        return True
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return False


class IframeSafeCookieMiddleware:
    """
    Request-aware proxy normalization, timezone activation, no-store cache
    protection for private views, and cookie policy for cross-site HTTPS
    iframes AND local HTTP development:

    - On external HTTPS requests (including behind Cloud Run + container nginx
      where X-Forwarded-Proto was overwritten to 'http' while X-Forwarded-Host
      carries the real HTTPS domain):
        1. Restores HTTP_X_FORWARDED_PROTO='https' BEFORE SessionMiddleware and
           CsrfViewMiddleware run so request.is_secure() is True and Django's
           Origin/Referer CSRF checks match the browser's https:// origin.
        2. Marks all response cookies (csrftoken, sessionid, logout deletions)
           with Path=/; SameSite=None; Secure; Partitioned (CHIPS) so modern
           browsers store and send cookies inside cross-site iframes.
    - Activates the user's browser IANA timezone (if present in `fittrack_tz`
      cookie) for the duration of the request so Daily & Weekly Reward Jar
      dates stay aligned with the user's local calendar across logout/login.
    - Applies strict `Cache-Control: no-store` headers on authenticated and
      auth-flow pages so browsers and bfcache never render stale jar progress.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_https = _is_external_https_request(request)
        if is_https:
            request.META["HTTP_X_FORWARDED_PROTO"] = "https"

        tz_activated = _activate_request_timezone(request)
        try:
            response = self.get_response(request)
        finally:
            if tz_activated:
                timezone.deactivate()

        user = getattr(request, "user", None)
        path = request.path or ""
        if (
            (user is not None and user.is_authenticated)
            or path.startswith(_NO_CACHE_PREFIXES)
        ) and not path.startswith("/static/"):
            add_never_cache_headers(response)
            response["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0, private"
            )
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
            patch_vary_headers(response, ("Cookie",))

        for cookie in response.cookies.values():
            if is_https:
                if not cookie.get("path"):
                    cookie["path"] = "/"
                cookie["samesite"] = "None"
                cookie["secure"] = True
                cookie["partitioned"] = True
            else:
                if str(cookie.get("samesite", "")).lower() == "none":
                    cookie["samesite"] = "Lax"
                cookie["secure"] = ""
                cookie["partitioned"] = ""

        return response
