from fastapi.testclient import TestClient

from backend.app.main import app, login_limiter


def _login(client: TestClient, password: str = "password") -> int:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": password}
    )
    return response.status_code


def test_password_change_success_then_login_with_new_password() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "new-strong-password-1"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        # Old password no longer works...
        client.post("/api/auth/logout")
        assert _login(client, "password") == 401

        # ...and the new one does.
        login_limiter.reset()  # the failed attempt above counts toward the limit
        assert _login(client, "new-strong-password-1") == 200


def test_password_change_rejects_wrong_current_password() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/auth/password",
            json={
                "current_password": "definitely-not-the-current-password",
                "new_password": "new-strong-password-1",
            },
        )
        assert resp.status_code == 401
        assert "incorrect" in resp.json()["error"].lower()

        # Original password still works.
        client.post("/api/auth/logout")
        login_limiter.reset()
        assert _login(client, "password") == 200


def test_password_change_rejects_short_new_password() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "short"},
        )
        assert resp.status_code == 422


def test_password_change_rejects_same_password() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "password"},
        )
        assert resp.status_code == 422
        assert "differ" in resp.json()["detail"].lower()


def test_password_change_requires_authentication() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/auth/password",
            json={"current_password": "password", "new_password": "new-strong-password-1"},
        )
        assert resp.status_code == 401


def test_password_change_respects_rate_limiter() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        # Pre-charge the IP's bucket up to the limit using wrong-current-password
        # attempts. The 11th attempt should be blocked by the limiter.
        for _ in range(10):
            client.post(
                "/api/auth/password",
                json={"current_password": "nope", "new_password": "new-strong-password-1"},
            )
        blocked = client.post(
            "/api/auth/password",
            json={"current_password": "nope", "new_password": "new-strong-password-1"},
        )
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
