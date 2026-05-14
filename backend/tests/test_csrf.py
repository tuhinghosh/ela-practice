from typing import Iterable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.csrf import CSRFOriginMiddleware
from backend.app.main import app as real_app


def _build_app(allowed: Iterable[str] = ()) -> FastAPI:
    """A minimal FastAPI app behind only the CSRF middleware so tests can
    exercise the middleware without pulling in session/auth state."""
    test_app = FastAPI()
    test_app.add_middleware(CSRFOriginMiddleware, allowed_origins=allowed)

    @test_app.get("/api/echo")
    def echo_get() -> dict:
        return {"ok": True}

    @test_app.post("/api/echo")
    def echo_post() -> dict:
        return {"ok": True}

    @test_app.post("/not-api/echo")
    def echo_non_api() -> dict:
        return {"ok": True}

    @test_app.post("/api/auth/login")
    def fake_login() -> dict:
        return {"ok": True}

    return test_app


def test_post_without_origin_is_allowed() -> None:
    with TestClient(_build_app()) as client:
        response = client.post("/api/echo", json={})
    assert response.status_code == 200


def test_post_with_matching_origin_is_allowed() -> None:
    with TestClient(_build_app(), base_url="http://testserver") as client:
        response = client.post("/api/echo", json={}, headers={"Origin": "http://testserver"})
    assert response.status_code == 200


def test_post_with_mismatched_origin_is_blocked() -> None:
    with TestClient(_build_app(), base_url="http://testserver") as client:
        response = client.post("/api/echo", json={}, headers={"Origin": "http://attacker.example"})
    assert response.status_code == 403
    assert "CSRF" in response.json()["error"]


def test_referer_used_when_origin_absent() -> None:
    with TestClient(_build_app(), base_url="http://testserver") as client:
        good = client.post(
            "/api/echo",
            json={},
            headers={"Referer": "http://testserver/some/page"},
        )
        bad = client.post(
            "/api/echo",
            json={},
            headers={"Referer": "http://attacker.example/landing"},
        )
    assert good.status_code == 200
    assert bad.status_code == 403


def test_get_with_bad_origin_is_allowed() -> None:
    with TestClient(_build_app(), base_url="http://testserver") as client:
        response = client.get("/api/echo", headers={"Origin": "http://attacker.example"})
    assert response.status_code == 200


def test_non_api_path_is_not_protected() -> None:
    with TestClient(_build_app(), base_url="http://testserver") as client:
        response = client.post(
            "/not-api/echo", json={}, headers={"Origin": "http://attacker.example"}
        )
    assert response.status_code == 200


def test_login_path_is_exempt() -> None:
    with TestClient(_build_app(), base_url="http://testserver") as client:
        response = client.post(
            "/api/auth/login", json={}, headers={"Origin": "http://attacker.example"}
        )
    assert response.status_code == 200


def test_allow_list_grants_explicit_origin() -> None:
    app = _build_app(allowed=["https://trusted.example"])
    with TestClient(app, base_url="http://testserver") as client:
        response = client.post(
            "/api/echo", json={}, headers={"Origin": "https://trusted.example"}
        )
    assert response.status_code == 200


def test_allow_list_accepts_bare_host_entries() -> None:
    app = _build_app(allowed=["trusted.example"])
    with TestClient(app, base_url="http://testserver") as client:
        response = client.post(
            "/api/echo", json={}, headers={"Origin": "https://trusted.example"}
        )
    assert response.status_code == 200


def test_malformed_origin_is_blocked() -> None:
    with TestClient(_build_app(), base_url="http://testserver") as client:
        response = client.post("/api/echo", json={}, headers={"Origin": "://"})
    assert response.status_code == 403


def test_real_app_login_remains_callable_with_cross_origin() -> None:
    """Smoke: the production app's /api/auth/login is exempt from CSRF so an
    attacker cannot use CSRF to deny logins, and so the test suite can
    continue logging in without setting Origin."""
    with TestClient(real_app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "password"},
            headers={"Origin": "http://attacker.example"},
        )
    assert response.status_code == 200


def test_real_app_blocks_cross_origin_submit() -> None:
    """An authenticated session with a malicious Origin cannot POST a submit."""
    with TestClient(real_app, base_url="http://testserver") as client:
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        response = client.post(
            "/api/activities/nature-01/submit",
            json={"responses": [{"question_id": "q1", "answer_choice": "anything"}]},
            headers={"Origin": "http://attacker.example"},
        )
    assert response.status_code == 403
    assert "CSRF" in response.json()["error"]


def test_config_parses_csrf_allowed_origins() -> None:
    from backend.app.config import load_settings

    settings = load_settings(
        env={"CSRF_ALLOWED_ORIGINS": "https://a.example, https://b.example , "}
    )
    assert settings.csrf_allowed_origins == ("https://a.example", "https://b.example")


def test_config_defaults_csrf_allowed_origins_empty() -> None:
    from backend.app.config import load_settings

    settings = load_settings(env={})
    assert settings.csrf_allowed_origins == ()
