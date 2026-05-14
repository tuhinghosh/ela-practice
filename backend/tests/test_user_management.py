from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.auth import hash_password, verify_password
from backend.app.config import DEV_BOOTSTRAP_PASSWORD, ConfigError, load_settings
from backend.app.db import get_connection
from backend.app.main import app


def test_hash_password_round_trip() -> None:
    encoded = hash_password("hunter2")
    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("hunter2", encoded) is True


def test_hash_password_uses_unique_salt_per_call() -> None:
    a = hash_password("hunter2")
    b = hash_password("hunter2")
    assert a != b
    assert verify_password("hunter2", a) is True
    assert verify_password("hunter2", b) is True


def test_verify_password_rejects_wrong_password() -> None:
    encoded = hash_password("hunter2")
    assert verify_password("not-it", encoded) is False


def test_verify_password_returns_false_for_unparseable_hash() -> None:
    assert verify_password("hunter2", "not-a-valid-encoded-hash") is False
    assert verify_password("hunter2", "scrypt$1$abc$xyz") is False
    assert verify_password("hunter2", "") is False


def test_seeded_user_login_succeeds_with_bootstrap_credentials() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "password"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["username"] == "user"
    assert body["role"] == "parent"


def test_login_rejects_wrong_password_for_seeded_user() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "definitely-not-the-password"},
        )
    assert response.status_code == 401


def test_login_rejects_unknown_user_without_db_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "stranger", "password": "anything"},
        )
    assert response.status_code == 401


def test_session_endpoint_returns_role_when_authenticated() -> None:
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        response = client.get("/api/auth/session")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["role"] == "parent"


def test_session_endpoint_returns_null_role_when_unauthenticated() -> None:
    with TestClient(app) as client:
        response = client.get("/api/auth/session")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is False
    assert body["role"] is None


def test_prod_requires_bootstrap_username() -> None:
    with pytest.raises(ConfigError, match="ELA_BOOTSTRAP_USERNAME is required"):
        load_settings(env={"ELA_ENV": "prod", "SESSION_SECRET": "x" * 32})


def test_prod_requires_bootstrap_password() -> None:
    with pytest.raises(ConfigError, match="ELA_BOOTSTRAP_PASSWORD is required"):
        load_settings(
            env={
                "ELA_ENV": "prod",
                "SESSION_SECRET": "x" * 32,
                "ELA_BOOTSTRAP_USERNAME": "admin",
            },
        )


def test_prod_rejects_dev_bootstrap_password() -> None:
    with pytest.raises(ConfigError, match="dev placeholder"):
        load_settings(
            env={
                "ELA_ENV": "prod",
                "SESSION_SECRET": "x" * 32,
                "ELA_BOOTSTRAP_USERNAME": "admin",
                "ELA_BOOTSTRAP_PASSWORD": DEV_BOOTSTRAP_PASSWORD,
            },
        )


def test_prod_accepts_real_bootstrap_credentials() -> None:
    settings = load_settings(
        env={
            "ELA_ENV": "prod",
            "SESSION_SECRET": "x" * 32,
            "ELA_BOOTSTRAP_USERNAME": "admin",
            "ELA_BOOTSTRAP_PASSWORD": "a-very-secure-password",
        },
    )
    assert settings.bootstrap_username == "admin"
    assert settings.bootstrap_password == "a-very-secure-password"


def test_dev_bootstrap_defaults_to_user_password() -> None:
    settings = load_settings(env={})
    assert settings.bootstrap_username == "user"
    assert settings.bootstrap_password == "password"


def _submit_nature_payload(client: TestClient) -> str:
    payload = {
        "responses": [
            {"question_id": "q1", "answer_choice": "The oak tree's roots took the water"},
            {"question_id": "q2", "answer_choice": "Healthy things that help plants grow"},
            {"question_id": "q3", "answer_choice": "Determined"},
            {
                "question_id": "q4",
                "answer_text": "Lila did not give up because she tried moving the pot.",
            },
        ]
    }
    response = client.post("/api/activities/nature-01/submit", json=payload)
    assert response.status_code == 200
    return response.json()["session_id"]


def test_tenant_isolation_blocks_cross_user_session_access(
    isolated_database: Path,
) -> None:
    # User A is the seeded bootstrap user; submit one activity so we have a
    # real session_id owned by them.
    with TestClient(app) as client_a:
        client_a.post("/api/auth/login", json={"username": "user", "password": "password"})
        session_id = _submit_nature_payload(client_a)

    # Insert a second parent + child profile directly into the same DB so we
    # can log in as a different account.
    second_hash = hash_password("second-password")
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'parent')",
            ("other-parent", second_hash),
        )
        other_user_id = connection.execute(
            "SELECT id FROM users WHERE username = ?", ("other-parent",)
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO child_profiles (user_id, display_name, grade_level) VALUES (?, ?, ?)",
            (other_user_id, "Other Kid", 3),
        )
        connection.execute(
            "INSERT INTO reward_state (user_id, stars, streak_days, badges_json) VALUES (?, 0, 0, '[]')",
            (other_user_id,),
        )
        connection.commit()

    with TestClient(app) as client_b:
        login = client_b.post(
            "/api/auth/login",
            json={"username": "other-parent", "password": "second-password"},
        )
        assert login.status_code == 200
        cross_access = client_b.get(f"/api/sessions/{session_id}")
        assert cross_access.status_code == 404
