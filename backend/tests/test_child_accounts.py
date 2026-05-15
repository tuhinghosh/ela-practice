"""Backend slice for per-user child accounts (iter N of CHILD_ACCOUNTS.md).

Covers:
- Migration #3 applied (schema shape, partial unique index, no UNIQUE on user_id)
- POST /api/parent/child-accounts profile-only and login-bearing paths
- Validation of display_name + username + password
- 403 for child caller
- Conflict on duplicate username
- GET /api/parent/child-accounts returns only this parent's children
- POST /api/parent/active-child/{id} validates ownership and writes session
- A freshly-created child user can log in via /api/auth/login
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.db import get_connection
from backend.app.main import app


def _login(client: TestClient, username: str = "user", password: str = "password") -> int:
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    ).status_code


def _make_child_caller(client: TestClient) -> None:
    """Flip the seeded user's role to 'child' so requests look like a
    child-role caller. Used to exercise the parent-only 403 branch."""
    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET role = 'child' WHERE username = ?", ("user",)
        )
        connection.commit()


def test_migration_three_shape(tmp_path: Path) -> None:
    """Fresh DB after ensure_database has the new child_profiles shape:
    login_user_id column, partial unique index, no UNIQUE on user_id."""
    from backend.app.db import ensure_database

    db_path = tmp_path / "shape.sqlite3"
    ensure_database(db_path)
    with get_connection(db_path) as connection:
        cols = {row["name"]: row for row in connection.execute("PRAGMA table_info(child_profiles)").fetchall()}
        assert "login_user_id" in cols
        assert "is_active" in cols

        # user_id no longer has its own UNIQUE constraint — the new
        # constraint surface lives on indexes instead.
        unique_indexes = [
            row for row in connection.execute("PRAGMA index_list(child_profiles)").fetchall()
            if row["unique"]
        ]
        assert any(idx["name"] == "idx_child_profiles_login_user_id" for idx in unique_indexes)

        # Partial unique index lets multiple NULLs coexist.
        connection.execute(
            "INSERT INTO child_profiles (user_id, display_name, grade_level) VALUES (?, ?, ?)",
            (1, "Second Kid", 3),
        )
        connection.execute(
            "INSERT INTO child_profiles (user_id, display_name, grade_level) VALUES (?, ?, ?)",
            (1, "Third Kid", 4),
        )
        connection.commit()
        count = connection.execute(
            "SELECT COUNT(*) AS n FROM child_profiles WHERE user_id = 1"
        ).fetchone()["n"]
        assert count >= 3  # seed Explorer Kid + two we just inserted


def test_create_child_account_profile_only() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/parent/child-accounts",
            json={"display_name": "Second Kid", "grade_level": 4},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["display_name"] == "Second Kid"
    assert body["grade_level"] == 4
    assert body["login_username"] is None


def test_create_child_account_with_login() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/parent/child-accounts",
            json={
                "display_name": "Mira",
                "grade_level": 3,
                "username": "mira",
                "password": "mira-secret-1",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["login_username"] == "mira"

    with get_connection() as connection:
        row = connection.execute(
            "SELECT role FROM users WHERE username = ?", ("mira",)
        ).fetchone()
    assert row is not None
    assert row["role"] == "child"


def test_create_child_account_validates_username_password_pairing() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/parent/child-accounts",
            json={"display_name": "Mira", "username": "mira"},
        )
    assert resp.status_code == 422
    assert "together" in resp.json()["detail"].lower()


def test_create_child_account_rejects_short_username() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/parent/child-accounts",
            json={
                "display_name": "Mira",
                "username": "mi",
                "password": "mira-secret-1",
            },
        )
    assert resp.status_code == 422
    assert "username" in resp.json()["detail"].lower()


def test_create_child_account_rejects_short_password() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        resp = client.post(
            "/api/parent/child-accounts",
            json={
                "display_name": "Mira",
                "username": "mira",
                "password": "short",
            },
        )
    assert resp.status_code == 422
    assert "password" in resp.json()["detail"].lower()


def test_create_child_account_rejects_duplicate_username() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        first = client.post(
            "/api/parent/child-accounts",
            json={
                "display_name": "Mira",
                "username": "mira",
                "password": "mira-secret-1",
            },
        )
        assert first.status_code == 201
        second = client.post(
            "/api/parent/child-accounts",
            json={
                "display_name": "Different Kid",
                "username": "mira",
                "password": "another-secret-1",
            },
        )
    assert second.status_code == 409
    assert "already in use" in second.json()["detail"].lower()


def test_create_child_account_403_for_child_caller() -> None:
    with TestClient(app) as client:
        # Re-role first then log in fresh so the session reflects child.
        _make_child_caller(client)
        assert _login(client) == 200
        resp = client.post(
            "/api/parent/child-accounts",
            json={"display_name": "Sneaky", "grade_level": 3},
        )
    assert resp.status_code == 403


def test_list_child_accounts_returns_only_owned() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        client.post(
            "/api/parent/child-accounts",
            json={"display_name": "Mira", "username": "mira", "password": "mira-secret-1"},
        )
        client.post(
            "/api/parent/child-accounts",
            json={"display_name": "Theo", "grade_level": 5},
        )

        # Insert a profile owned by a different parent so we can prove
        # tenant isolation on the list query.
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'parent')",
                ("other-parent", "pbkdf2_sha256$1000$YWFh$YWFh"),
            )
            other = connection.execute(
                "SELECT id FROM users WHERE username = ?", ("other-parent",)
            ).fetchone()["id"]
            connection.execute(
                "INSERT INTO child_profiles (user_id, display_name, grade_level) VALUES (?, ?, ?)",
                (other, "Stranger", 3),
            )
            connection.commit()

        listed = client.get("/api/parent/child-accounts").json()

    names = {entry["display_name"] for entry in listed["children"]}
    assert {"Explorer Kid", "Mira", "Theo"}.issubset(names)
    assert "Stranger" not in names


def test_set_active_child_profile_writes_session() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        new_resp = client.post(
            "/api/parent/child-accounts",
            json={"display_name": "Theo", "grade_level": 5},
        )
        new_id = new_resp.json()["id"]
        resp = client.post(f"/api/parent/active-child/{new_id}")
        assert resp.status_code == 200
        assert resp.json()["active_child_profile_id"] == new_id


def test_set_active_child_profile_404_for_unowned() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'parent')",
                ("other-parent", "pbkdf2_sha256$1000$YWFh$YWFh"),
            )
            other = connection.execute(
                "SELECT id FROM users WHERE username = ?", ("other-parent",)
            ).fetchone()["id"]
            connection.execute(
                "INSERT INTO child_profiles (user_id, display_name, grade_level) VALUES (?, ?, ?)",
                (other, "Stranger", 3),
            )
            stranger_id = connection.execute(
                "SELECT id FROM child_profiles WHERE display_name = 'Stranger'"
            ).fetchone()["id"]
            connection.commit()

        resp = client.post(f"/api/parent/active-child/{stranger_id}")
    assert resp.status_code == 404


def test_child_user_can_log_in_after_creation() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        create = client.post(
            "/api/parent/child-accounts",
            json={"display_name": "Mira", "username": "mira", "password": "mira-secret-1"},
        )
        assert create.status_code == 201

        # Parent logs out so we're on a clean slate.
        client.post("/api/auth/logout")

        login = client.post(
            "/api/auth/login", json={"username": "mira", "password": "mira-secret-1"}
        )
        assert login.status_code == 200
        body = login.json()
        assert body["authenticated"] is True
        assert body["username"] == "mira"
        assert body["role"] == "child"


def test_resolve_active_child_profile_for_parent_picks_first(tmp_path: Path) -> None:
    """Unit-test the resolver directly so we can assert behavior without a
    full request cycle."""
    from backend.app.db import ensure_database, get_user_by_username
    from backend.app.main import _resolve_active_child_profile

    db_path = tmp_path / "resolve.sqlite3"
    ensure_database(db_path)

    class FakeSession(dict):
        pass

    class FakeRequest:
        def __init__(self, role: str) -> None:
            self.session = FakeSession({"authenticated": True, "username": "user", "role": role})

    with get_connection(db_path) as connection:
        parent = get_user_by_username(connection, "user")
        request = FakeRequest("parent")
        profile = _resolve_active_child_profile(connection, request, parent)
        assert profile is not None
        assert profile["display_name"] == "Explorer Kid"
