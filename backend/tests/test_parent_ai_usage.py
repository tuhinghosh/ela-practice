"""/api/progress/parent surfaces today's AI call usage so parents can
sanity-check OpenRouter spend without reading server logs."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app, ai_quota


def _login(client: TestClient) -> int:
    return client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    ).status_code


def test_ai_usage_block_shape_when_enabled() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        # Charge two AI calls to the seeded parent (user_id=1).
        ai_quota.register(user_id=1)
        ai_quota.register(user_id=1)

        body = client.get("/api/progress/parent").json()

    usage = body["ai_usage"]
    assert usage["enabled"] is True
    assert usage["used"] == 2
    assert usage["limit"] == 50
    assert usage["remaining"] == 48
    assert usage["reset_at"]  # ISO-8601 string


def test_ai_usage_zero_before_any_call() -> None:
    with TestClient(app) as client:
        assert _login(client) == 200
        body = client.get("/api/progress/parent").json()

    usage = body["ai_usage"]
    assert usage["used"] == 0
    assert usage["remaining"] == usage["limit"]


def test_ai_usage_remaining_is_null_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the limit is disabled (set to 0) the response should still
    show usage but flag the absence of a cap so the UI can render
    something sensible ("Unlimited") rather than a misleading 0."""
    from backend.app.ai_quota import DailyAICallQuota, SQLiteQuotaStore
    from backend.app import main as main_module
    from backend.app.db import get_connection

    monkeypatch.setattr(
        main_module,
        "ai_quota",
        DailyAICallQuota(daily_limit=0, store=SQLiteQuotaStore(get_connection)),
    )

    with TestClient(app) as client:
        assert _login(client) == 200
        # The replacement quota is still backed by the same DB, so
        # registering a call here is a useful exercise.
        main_module.ai_quota.register(user_id=1)
        body = client.get("/api/progress/parent").json()

    usage = body["ai_usage"]
    assert usage["enabled"] is False
    assert usage["used"] == 1
    assert usage["remaining"] is None


def test_ai_usage_reflects_actual_endpoint_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hitting the AI coach endpoint should increment the count surfaced
    on the parent endpoint."""
    monkeypatch.setattr(
        "backend.app.main.generate_ai_coach_output",
        lambda *_args, **_kwargs: {
            "message_to_child": "msg",
            "explanation": "exp",
            "celebration": "yay",
            "confidence": 0.5,
            "used_fallback": False,
            "model": "x",
            "suggested_next_activity_id": None,
            "hint": None,
        },
    )

    with TestClient(app) as client:
        assert _login(client) == 200
        submit = client.post(
            "/api/activities/nature-01/submit",
            json={
                "responses": [
                    {"question_id": "q1", "answer_choice": "The oak tree's roots took the water"},
                    {"question_id": "q2", "answer_choice": "Healthy things that help plants grow"},
                    {"question_id": "q3", "answer_choice": "Determined"},
                    {"question_id": "q4", "answer_text": "Lila kept trying."},
                ]
            },
        )
        assert submit.status_code == 200
        session_id = submit.json()["session_id"]

        before = client.get("/api/progress/parent").json()["ai_usage"]["used"]

        coach = client.post("/api/ai/coach", json={"session_id": session_id})
        assert coach.status_code == 200

        after = client.get("/api/progress/parent").json()["ai_usage"]["used"]

    assert after == before + 1
