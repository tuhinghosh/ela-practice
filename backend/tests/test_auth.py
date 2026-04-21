from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app import main


def _write_static_files(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "index.html").write_text("<html><body>Home</body></html>", encoding="utf-8")
    login_dir = target / "login"
    login_dir.mkdir(parents=True, exist_ok=True)
    (login_dir / "index.html").write_text("<html><body>Login</body></html>", encoding="utf-8")


@pytest.mark.asyncio
async def test_login_failure_returns_401() -> None:
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"username": "wrong", "password": "nope"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_session_and_logout_flow() -> None:
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_response = await client.post(
            "/api/auth/login",
            json={"username": "user", "password": "password"},
        )
        assert login_response.status_code == 200

        session_response = await client.get("/api/auth/session")
        assert session_response.status_code == 200
        assert session_response.json()["authenticated"] is True

        logout_response = await client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        post_logout_session = await client.get("/api/auth/session")
        assert post_logout_session.status_code == 200
        assert post_logout_session.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_protected_route_redirects_without_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    static_dir = tmp_path / "static"
    _write_static_files(static_dir)
    monkeypatch.setattr(main, "STATIC_DIR", static_dir)

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        response = await client.get("/")

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_invalid_session_cookie_is_not_authenticated() -> None:
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("ela_session", "tampered-cookie-value")
        response = await client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_path_traversal_is_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    static_dir = tmp_path / "static"
    _write_static_files(static_dir)
    monkeypatch.setattr(main, "STATIC_DIR", static_dir)

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("sensitive data", encoding="utf-8")

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/api/auth/login", json={"username": "user", "password": "password"})
        assert login.status_code == 200

        traversal = await client.get("/../secret.txt")
        assert b"sensitive data" not in traversal.content

        traversal2 = await client.get("/..%2F..%2Fetc/passwd")
        assert traversal2.status_code in (200, 302)
        assert b"root:" not in traversal2.content
