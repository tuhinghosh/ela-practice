"""Tests for X-Forwarded-For handling via uvicorn ProxyHeadersMiddleware.

Why this matters: behind a reverse proxy (Railway, Fly, Cloudflare,
nginx, etc.) every request to the container looks like it came from the
proxy's IP. Without the rewrite, our per-IP login rate limiter collapses
all traffic into one bucket. With the rewrite, ``request.client.host``
reflects the original client (per X-Forwarded-For) and the limiter
behaves correctly.

The middleware ONLY rewrites when the immediate hop is in
``trusted_hosts`` — operators behind a proxy they control should set
``TRUSTED_PROXY_IPS=*``; everyone else leaves it empty (the default)
to ignore the header entirely.
"""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from backend.app.main import app as real_app, login_limiter


def _echo_app(trusted_hosts: str) -> FastAPI:
    inner = FastAPI()

    @inner.get("/whoami")
    def whoami(request: Request) -> dict:
        return {"client": request.client.host if request.client else None}

    return ProxyHeadersMiddleware(inner, trusted_hosts=trusted_hosts)


def test_x_forwarded_for_is_honored_when_trusted() -> None:
    with TestClient(_echo_app(trusted_hosts="*")) as client:
        response = client.get("/whoami", headers={"X-Forwarded-For": "203.0.113.7"})
    assert response.status_code == 200
    assert response.json()["client"] == "203.0.113.7"


def test_x_forwarded_for_is_ignored_when_not_trusted() -> None:
    # Empty trusted_hosts (the default in our config) → never rewrite,
    # even when X-Forwarded-For is present.
    with TestClient(_echo_app(trusted_hosts="")) as client:
        response = client.get("/whoami", headers={"X-Forwarded-For": "203.0.113.7"})
    assert response.status_code == 200
    assert response.json()["client"] != "203.0.113.7"


def test_x_forwarded_for_takes_leftmost_entry_when_multiple_hops() -> None:
    """Convention: leftmost is the original client; everything after is a
    chain of proxies. The middleware should honor that ordering."""
    with TestClient(_echo_app(trusted_hosts="*")) as client:
        response = client.get(
            "/whoami",
            headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1, 10.0.0.2"},
        )
    assert response.json()["client"] == "203.0.113.7"


def test_login_rate_limit_no_longer_collapses_behind_a_trusted_proxy(
    monkeypatch,
) -> None:
    """The headline guarantee: with the proxy middleware trusting the
    immediate hop, eleven failed logins from eleven *different* forwarded
    IPs do not trip the per-IP rate limit. Without the rewrite, they
    would all share one bucket and the 11th would 429."""
    # The middleware was constructed at import time with empty trusted
    # hosts; flip it on the live instance to simulate the env var being
    # set in a real deploy.
    user_middleware = real_app.user_middleware
    proxy_layer = next(
        layer for layer in user_middleware if layer.cls is ProxyHeadersMiddleware
    )
    monkeypatch.setitem(proxy_layer.kwargs, "trusted_hosts", "*")
    real_app.middleware_stack = real_app.build_middleware_stack()
    login_limiter.reset()

    with TestClient(real_app) as client:
        for i in range(11):
            response = client.post(
                "/api/auth/login",
                json={"username": "user", "password": "wrong"},
                headers={"X-Forwarded-For": f"198.51.100.{i + 1}"},
            )
            # Each "IP" sees its own first failure, so no 429.
            assert response.status_code == 401, (
                f"call {i} unexpectedly returned {response.status_code}"
            )

    # Rebuild the stack with the original (empty) trust to leave state
    # clean for other tests.
    monkeypatch.setitem(proxy_layer.kwargs, "trusted_hosts", "")
    real_app.middleware_stack = real_app.build_middleware_stack()


def test_login_rate_limit_still_works_for_a_single_client(monkeypatch) -> None:
    """Counterpoint: with trust on, a single attacker repeatedly hitting
    from the same X-Forwarded-For *does* trip the limit on the 11th try.
    Proves the rewrite is per-call, not "always allow"."""
    user_middleware = real_app.user_middleware
    proxy_layer = next(
        layer for layer in user_middleware if layer.cls is ProxyHeadersMiddleware
    )
    monkeypatch.setitem(proxy_layer.kwargs, "trusted_hosts", "*")
    real_app.middleware_stack = real_app.build_middleware_stack()
    login_limiter.reset()

    fake_ip = "198.51.100.99"
    try:
        with TestClient(real_app) as client:
            for _ in range(10):
                response = client.post(
                    "/api/auth/login",
                    json={"username": "user", "password": "wrong"},
                    headers={"X-Forwarded-For": fake_ip},
                )
                assert response.status_code == 401

            blocked = client.post(
                "/api/auth/login",
                json={"username": "user", "password": "wrong"},
                headers={"X-Forwarded-For": fake_ip},
            )
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
    finally:
        monkeypatch.setitem(proxy_layer.kwargs, "trusted_hosts", "")
        real_app.middleware_stack = real_app.build_middleware_stack()


def test_config_default_trusted_proxy_ips_is_empty_string() -> None:
    from backend.app.config import load_settings

    settings = load_settings(env={})
    assert settings.trusted_proxy_ips == ""


def test_config_accepts_wildcard_trusted_proxy_ips() -> None:
    from backend.app.config import load_settings

    settings = load_settings(env={"TRUSTED_PROXY_IPS": "*"})
    assert settings.trusted_proxy_ips == "*"


def test_config_accepts_comma_separated_trusted_proxy_ips() -> None:
    from backend.app.config import load_settings

    settings = load_settings(
        env={"TRUSTED_PROXY_IPS": "127.0.0.1, 10.0.0.5"}
    )
    assert settings.trusted_proxy_ips == "127.0.0.1, 10.0.0.5"
