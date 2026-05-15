"""Tests for the hot content reload admin endpoint."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.content_schema import list_seed_activities
from backend.app.db import get_connection
from backend.app.main import app


def test_reload_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/api/admin/content/reload")
    assert response.status_code == 401


def test_reload_rejects_non_parent_role() -> None:
    with TestClient(app) as client:
        # Authenticate normally then swap the session role to 'child'. The
        # SessionMiddleware stores role in the signed cookie; the simplest
        # way to simulate a child-role session is to mark the seeded user
        # row as a child and re-login.
        with get_connection() as connection:
            connection.execute(
                "UPDATE users SET role = 'child' WHERE username = ?", ("user",)
            )
            connection.commit()

        login = client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        )
        assert login.status_code == 200
        assert login.json()["role"] == "child"

        response = client.post("/api/admin/content/reload")
    assert response.status_code == 403
    assert "parent" in response.json()["detail"].lower()


def test_reload_returns_counts_and_clears_cache() -> None:
    # Warm the cache first.
    list_seed_activities.cache_clear()
    list_seed_activities()
    assert list_seed_activities.cache_info().currsize == 1

    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200

        response = client.post("/api/admin/content/reload")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["activity_count"] >= 50
    assert body["theme_count"] >= 5
    assert body["content_version"]

    # The endpoint cleared then re-populated the cache, so a hit count
    # corresponding to the latest activities is in place.
    assert list_seed_activities.cache_info().currsize == 1


def test_reload_returns_500_on_manifest_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import backend.app.content_schema as schema_module
    import backend.app.main as main_module

    fake_manifest = tmp_path / "MANIFEST.json"
    # Manifest claims an obviously wrong hash for activities.json.
    fake_manifest.write_text(
        '{"content_version":"0.0.0","files":{"activities.json":"' + "00" * 32 + '"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(schema_module, "MANIFEST_FILE", fake_manifest)
    monkeypatch.setattr(main_module, "verify_content_manifest", schema_module.verify_content_manifest)

    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200
        response = client.post("/api/admin/content/reload")

    assert response.status_code == 500
    assert "checksum mismatch" in response.json()["detail"].lower()
