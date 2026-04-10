from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import ai_client
from backend.app.ai_client import (
    MissingOpenRouterKeyError,
    OpenRouterProviderError,
    OpenRouterTimeoutError,
    run_openrouter_connectivity_check,
)
from backend.app.main import app


def test_connectivity_succeeds_when_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_post(_: dict, timeout_s: float) -> dict:
        assert timeout_s > 0
        return {
            "choices": [
                {
                    "message": {
                        "content": "4",
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_client, "_post_chat_completion", fake_post)
    result = run_openrouter_connectivity_check(prompt="2+2")

    assert result["response_text"] == "4"
    assert result["model"] == "openai/gpt-oss-120b"


def test_missing_key_fails_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(MissingOpenRouterKeyError):
        run_openrouter_connectivity_check(prompt="2+2")


@pytest.mark.parametrize(
    "exc_type",
    [OpenRouterTimeoutError, OpenRouterProviderError],
)
def test_timeout_or_provider_fails_safely(monkeypatch: pytest.MonkeyPatch, exc_type: type[Exception]) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_post(_: dict, timeout_s: float) -> dict:
        raise exc_type("boom")

    monkeypatch.setattr(ai_client, "_post_chat_completion", fake_post)
    with pytest.raises(exc_type):
        run_openrouter_connectivity_check(prompt="2+2")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "ai-api-test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    with TestClient(app) as test_client:
        login = test_client.post("/api/auth/login", json={"username": "user", "password": "password"})
        assert login.status_code == 200
        yield test_client


def test_connectivity_route_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(prompt: str) -> dict:
        assert prompt == "2+2"
        return {"model": "openai/gpt-oss-120b", "prompt": prompt, "response_text": "4"}

    monkeypatch.setattr("backend.app.main.run_openrouter_connectivity_check", fake_check)
    response = client.post("/api/ai/connectivity-check", json={"prompt": "2+2"})
    assert response.status_code == 200
    assert response.json()["response_text"] == "4"


def test_connectivity_route_missing_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(prompt: str) -> dict:
        raise MissingOpenRouterKeyError("OPENROUTER_API_KEY is not configured.")

    monkeypatch.setattr("backend.app.main.run_openrouter_connectivity_check", fake_check)
    response = client.post("/api/ai/connectivity-check", json={"prompt": "2+2"})
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_connectivity_route_provider_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(prompt: str) -> dict:
        raise OpenRouterProviderError("provider failed")

    monkeypatch.setattr("backend.app.main.run_openrouter_connectivity_check", fake_check)
    response = client.post("/api/ai/connectivity-check", json={"prompt": "2+2"})
    assert response.status_code == 502
    assert "provider error" in response.json()["detail"].lower()
