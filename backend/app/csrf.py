"""CSRF defense via Origin/Referer header validation.

We use cookie-based sessions, so a malicious site that tricks the user into
issuing a cross-site state-changing request would carry the session cookie
along (modulo SameSite=Lax, which already blocks most of these). This layer
is the belt to that suspenders: for unsafe HTTP methods targeting ``/api/*``
we require the ``Origin`` (or fallback ``Referer``) header to match the
host the request is being served on, or to be listed in
``Settings.csrf_allowed_origins``.

Why Origin and not a double-submit cookie / synchronizer token:

- Browsers always send ``Origin`` on cross-origin POSTs (per Fetch spec), so
  the header is reliably present in the threat scenario.
- It needs no frontend or test-client changes — non-browser clients (curl,
  TestClient) simply omit ``Origin`` and pass through. They cannot ride a
  victim's session cookie either way, so the threat does not apply to them.
- Same-origin POSTs from our SPA also send ``Origin`` matching the host,
  so they pass naturally.

``/api/auth/login`` is intentionally exempt because the user has no
session cookie yet when they first authenticate. Login is gated by hashed
password verification and per-IP rate limiting (see ``rate_limit.py``).
"""
from __future__ import annotations

from typing import Awaitable, Callable, Iterable, Set
from urllib.parse import urlparse

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
EXEMPT_PATHS = frozenset({"/api/auth/login"})
PROTECTED_PATH_PREFIX = "/api/"


def _origin_host(origin: str) -> str:
    """Return ``host[:port]`` from an Origin/Referer value, or '' if unparseable."""
    if not origin:
        return ""
    parsed = urlparse(origin if "://" in origin else f"http://{origin}")
    return parsed.netloc.lower()


def _request_self_origins(request: Request) -> Set[str]:
    """Origins that should be treated as same-site for this request."""
    hosts: Set[str] = set()
    url_host = (request.url.netloc or "").lower()
    if url_host:
        hosts.add(url_host)
    header_host = request.headers.get("host", "").lower()
    if header_host:
        hosts.add(header_host)
    return hosts


class CSRFOriginMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_origins: Iterable[str]) -> None:
        super().__init__(app)
        self._allowed = {entry.strip().lower() for entry in allowed_origins if entry.strip()}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)
        path = request.url.path
        if not path.startswith(PROTECTED_PATH_PREFIX):
            return await call_next(request)
        if path in EXEMPT_PATHS:
            return await call_next(request)

        origin_header = request.headers.get("origin") or request.headers.get("referer", "")
        if not origin_header:
            # Non-browser clients (curl, tests, server-to-server) cannot ride
            # a victim's session cookie, so omitting Origin is not a CSRF
            # vector. Let them through.
            return await call_next(request)

        origin_host = _origin_host(origin_header)
        if not origin_host:
            return _forbidden("Origin header is malformed.")

        allowed = _request_self_origins(request) | self._allowed
        # Also tolerate full-URL entries like https://example.com in config.
        allowed_hosts = {_origin_host(entry) or entry for entry in allowed}

        if origin_host in allowed_hosts:
            return await call_next(request)

        return _forbidden(f'Origin "{origin_header}" is not allowed.')


def _forbidden(detail: str) -> Response:
    return JSONResponse(
        {"error": "CSRF check failed", "detail": detail},
        status_code=status.HTTP_403_FORBIDDEN,
    )
