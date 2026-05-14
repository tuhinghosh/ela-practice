"""Tests for the observability stack: JSON logging, request middleware,
/api/ready, AI quota, AI call instrumentation."""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import ai_client
from backend.app.ai_quota import DailyAICallQuota
from backend.app.logging_config import JsonLogFormatter, configure_logging
from backend.app.main import app, ai_quota


def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonLogFormatter().format(record))


def test_json_formatter_emits_required_fields() -> None:
    record = logging.LogRecord(
        name="ela.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=None,
        exc_info=None,
    )
    payload = _format(record)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "ela.test"
    assert payload["message"] == "hello"
    assert "timestamp" in payload


def test_json_formatter_propagates_extras() -> None:
    logger = logging.getLogger("ela.extras")
    logger.handlers = []
    logger.propagate = False
    captured: list[logging.LogRecord] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    logger.addHandler(CaptureHandler())
    logger.setLevel(logging.INFO)

    logger.info("event-x", extra={"request_id": "abc", "status_code": 200})
    payload = _format(captured[0])
    assert payload["request_id"] == "abc"
    assert payload["status_code"] == 200


def test_json_formatter_handles_unserializable_extras() -> None:
    record = logging.LogRecord(
        name="ela.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hi",
        args=None,
        exc_info=None,
    )
    record.weird = object()  # not JSON-serializable
    payload = _format(record)
    assert "weird" in payload
    assert isinstance(payload["weird"], str)


def test_configure_logging_is_idempotent() -> None:
    configure_logging("INFO")
    configure_logging("INFO")
    root = logging.getLogger()
    ela_handlers = [h for h in root.handlers if getattr(h, "_ela_json", False)]
    assert len(ela_handlers) == 1


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_endpoint_reports_migrations_applied() -> None:
    with TestClient(app) as client:
        response = client.get("/api/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["migrations_applied"] >= 1


def test_ready_endpoint_returns_503_when_db_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app import main as main_module

    def broken_connection(*_args, **_kwargs):
        raise RuntimeError("simulated DB outage")

    monkeypatch.setattr(main_module, "get_connection", broken_connection)
    with TestClient(app) as client:
        response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_request_middleware_logs_method_path_status_duration(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="ela.request"):
        with TestClient(app) as client:
            client.get("/api/health")

    matching = [r for r in caplog.records if getattr(r, "event", None) == "http_request"]
    assert any(
        r.method == "GET" and r.path == "/api/health" and r.status_code == 200
        and isinstance(r.duration_ms, (int, float))
        for r in matching
    )


def test_ai_client_logs_success_with_model_and_duration(
    caplog, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        ai_client,
        "_post_chat_completion",
        lambda payload, timeout_s: {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
        },
    )
    with caplog.at_level(logging.INFO, logger="ela.ai_call"):
        result = ai_client.run_openrouter_chat([{"role": "user", "content": "hi"}])
    assert result["response_text"] == "ok"
    records = [r for r in caplog.records if getattr(r, "event", None) == "ai_call"]
    assert records, "expected at least one ai_call log record"
    rec = records[-1]
    assert rec.status == "ok"
    assert rec.error_class is None
    assert rec.model
    assert rec.duration_ms >= 0
    assert rec.prompt_tokens == 3
    assert rec.completion_tokens == 5


def test_ai_client_logs_failure_with_error_class(
    caplog, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def explode(payload, timeout_s):
        raise ai_client.OpenRouterProviderError("boom")

    monkeypatch.setattr(ai_client, "_post_chat_completion", explode)
    with caplog.at_level(logging.INFO, logger="ela.ai_call"):
        with pytest.raises(ai_client.OpenRouterProviderError):
            ai_client.run_openrouter_chat([{"role": "user", "content": "hi"}])
    rec = next(r for r in caplog.records if getattr(r, "event", None) == "ai_call")
    assert rec.status == "error"
    assert rec.error_class == "OpenRouterProviderError"


def test_ai_quota_allows_under_limit_and_blocks_over_limit() -> None:
    quota = DailyAICallQuota(daily_limit=3)
    for _ in range(3):
        assert quota.register(user_id=1).allowed is True
    fourth = quota.register(user_id=1)
    assert fourth.allowed is False
    assert fourth.used == 4
    assert fourth.limit == 3


def test_ai_quota_separates_users() -> None:
    quota = DailyAICallQuota(daily_limit=1)
    assert quota.register(user_id=1).allowed is True
    assert quota.register(user_id=2).allowed is True
    assert quota.register(user_id=1).allowed is False
    assert quota.register(user_id=2).allowed is False


def test_ai_quota_resets_on_day_rollover() -> None:
    clock_state = [datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)]
    quota = DailyAICallQuota(daily_limit=2, clock=lambda: clock_state[0])
    quota.register(user_id=1)
    quota.register(user_id=1)
    assert quota.check(user_id=1).allowed is False

    clock_state[0] = datetime(2026, 5, 15, 0, 5, tzinfo=timezone.utc)
    assert quota.check(user_id=1).allowed is True


def test_ai_quota_zero_disables_limiting() -> None:
    quota = DailyAICallQuota(daily_limit=0)
    assert quota.is_enabled is False
    for _ in range(100):
        assert quota.register(user_id=1).allowed is True


def test_ai_coach_endpoint_returns_429_when_quota_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
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

    # Pre-charge the quota up to the limit for the seeded user (id=1 in a
    # freshly seeded DB).
    for _ in range(ai_quota._daily_limit):  # type: ignore[attr-defined]
        ai_quota.register(user_id=1)

    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200

        # Submit something so there's a session to coach against.
        submit = client.post(
            "/api/activities/nature-01/submit",
            json={
                "responses": [
                    {"question_id": "q1", "answer_choice": "The oak tree's roots took the water"},
                    {"question_id": "q2", "answer_choice": "x"},
                    {"question_id": "q3", "answer_choice": "Determined"},
                    {"question_id": "q4", "answer_text": "Lila kept trying."},
                ]
            },
        )
        assert submit.status_code == 200
        session_id = submit.json()["session_id"]

        # Quota is exhausted; coach call should be rejected.
        response = client.post(
            "/api/ai/coach",
            json={"session_id": session_id},
        )

    assert response.status_code == 429
    body = response.json()
    assert "limit" in body["error"].lower()
    assert "reset_at" in body
