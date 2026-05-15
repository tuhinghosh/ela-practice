"""Tests for the iter-21 slice: route role-gates + active-child resolver.

- /api/progress/parent and /api/ai/connectivity-check now return 403
  for a child-role caller (parent-only).
- /api/dashboard resolves the active child profile and honors a
  parent's active-child selection.
- A child-role caller's /api/dashboard surfaces their own profile,
  not their parent's.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.db import get_connection
from backend.app.main import app


def _login(client: TestClient, username: str = "user", password: str = "password") -> int:
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    ).status_code


def _make_child_seed_user() -> None:
    """Flip the seeded user row from parent to child so requests look like a
    child-role caller without going through the parent-creates-child path."""
    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET role = 'child' WHERE username = ?", ("user",)
        )
        # Link the seeded child profile to this same user so the resolver
        # finds a match in the child branch.
        seeded_child_id = connection.execute(
            "SELECT id FROM child_profiles WHERE display_name = 'Explorer Kid'"
        ).fetchone()["id"]
        seeded_user_id = connection.execute(
            "SELECT id FROM users WHERE username = 'user'"
        ).fetchone()["id"]
        connection.execute(
            "UPDATE child_profiles SET login_user_id = ? WHERE id = ?",
            (seeded_user_id, seeded_child_id),
        )
        connection.commit()


def test_parent_progress_rejects_child_role() -> None:
    with TestClient(app) as client:
        _make_child_seed_user()
        assert _login(client) == 200
        response = client.get("/api/progress/parent")
    assert response.status_code == 403
    assert "parent" in response.json()["detail"].lower()


def test_connectivity_check_rejects_child_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mock OpenRouter so a parent call would otherwise succeed; this
    # isolates the role-gate as the rejection cause.
    monkeypatch.setattr(
        "backend.app.main.run_openrouter_connectivity_check",
        lambda prompt: {"model": "x", "prompt": prompt, "response_text": "4"},
    )
    with TestClient(app) as client:
        _make_child_seed_user()
        assert _login(client) == 200
        response = client.post(
            "/api/ai/connectivity-check", json={"prompt": "2+2"}
        )
    assert response.status_code == 403


def test_child_dashboard_resolves_to_own_profile() -> None:
    with TestClient(app) as client:
        # As the seeded parent, create a child user "mira" with her own login.
        assert _login(client) == 200
        new = client.post(
            "/api/parent/child-accounts",
            json={
                "display_name": "Mira",
                "grade_level": 4,
                "username": "mira",
                "password": "mira-secret-1",
            },
        )
        assert new.status_code == 201
        client.post("/api/auth/logout")

        # Mira logs in directly; her dashboard should show HER profile,
        # not the seeded "Explorer Kid" linked to the parent.
        assert _login(client, "mira", "mira-secret-1") == 200
        dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["child_profile"]["display_name"] == "Mira"
    assert body["child_profile"]["grade_level"] == 4


def test_parent_dashboard_follows_active_child_selection() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200

        # Parent now owns three profiles: the seeded "Explorer Kid" + two
        # new ones. By default the resolver returns the first by id.
        for display, grade in (("Theo", 5), ("Mira", 4)):
            response = client.post(
                "/api/parent/child-accounts",
                json={"display_name": display, "grade_level": grade},
            )
            assert response.status_code == 201

        initial = client.get("/api/dashboard").json()
        assert initial["child_profile"]["display_name"] == "Explorer Kid"

        # Switch to "Mira" via the iter-20 active-child endpoint and
        # confirm the dashboard reflects the switch.
        listed = client.get("/api/parent/child-accounts").json()["children"]
        mira_id = next(c["id"] for c in listed if c["display_name"] == "Mira")
        switch = client.post(f"/api/parent/active-child/{mira_id}")
        assert switch.status_code == 200

        switched = client.get("/api/dashboard").json()
        assert switched["child_profile"]["display_name"] == "Mira"
        assert switched["child_profile"]["grade_level"] == 4

        # Switch to "Theo".
        theo_id = next(c["id"] for c in listed if c["display_name"] == "Theo")
        client.post(f"/api/parent/active-child/{theo_id}")
        again = client.get("/api/dashboard").json()
        assert again["child_profile"]["display_name"] == "Theo"


def test_dashboard_400_when_no_child_resolvable() -> None:
    """A child-role caller with no linked profile should get a clean 400,
    not a 500 from a sqlite3.Row-None unpack."""
    with TestClient(app) as client:
        # Build a child user that has no child_profile linked to it.
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash, role) "
                "VALUES (?, ?, 'child')",
                ("orphan", "pbkdf2_sha256$1000$YWFh$YWFh"),
            )
            connection.commit()

        # Build a known password for the orphan via the parent rotation
        # path is overkill — just create with a real hash.
        from backend.app.auth import hash_password

        with get_connection() as connection:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (hash_password("orphan-secret-1"), "orphan"),
            )
            connection.commit()

        assert _login(client, "orphan", "orphan-secret-1") == 200
        dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 400
    assert "no active child profile" in dashboard.json()["detail"].lower()
