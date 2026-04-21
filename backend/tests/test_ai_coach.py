from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import ai_coach
from backend.app.ai_client import MissingOpenRouterKeyError, OpenRouterProviderError
from backend.app.ai_coach import (
    build_ai_coach_system_prompt,
    build_ai_coach_user_prompt,
    generate_ai_coach_output,
)
from backend.app.main import app


def _sample_context() -> dict:
    return {
        "activity_title": "Forest Friends",
        "score_percent": 85,
        "rubric": {
            "completion": "meets",
            "relevance": "meets",
            "sentence_completeness": "needs_work",
            "skill_specific_checks": ["evidence reference"],
        },
        "skill_breakdown": {"inference": 85, "short-writing": 80},
        "strengths": ["inference"],
        "growth_areas": ["sentence-quality"],
    }


def test_prompt_construction_includes_relevant_context_only() -> None:
    prompt = build_ai_coach_user_prompt(_sample_context(), child_question="Can I do better next time?")
    assert "activity_title: Forest Friends" in prompt
    assert "score_percent: 85" in prompt
    assert "optional_child_question: Can I do better next time?" in prompt
    assert "chat history" not in prompt.lower()


def test_safety_system_prompt_is_bounded() -> None:
    prompt = build_ai_coach_system_prompt()
    assert "child-safe" in prompt
    assert "school-appropriate" in prompt
    assert "Return only valid JSON" in prompt
    assert "unrelated" in prompt


def test_structured_output_parsing_success(monkeypatch: pytest.MonkeyPatch) -> None:
    valid_json = """{
      "message_to_child": "You did great work using evidence.",
      "message_to_parent": "Strong effort today.",
      "hint": "Use clue words from the passage.",
      "explanation": "Good answers point to text details.",
      "celebration": "Nice reading quest!",
      "suggested_next_activity_id": "river-map",
      "suggested_skill_tag": "inference",
      "writing_feedback": "Add one more complete sentence.",
      "confidence": 0.88
    }"""

    captured = {}

    def fake_chat(messages, **kwargs):
        captured["kwargs"] = kwargs
        return {"model": "openai/gpt-oss-120b", "response_text": valid_json}

    monkeypatch.setattr(ai_coach, "run_openrouter_chat", fake_chat)
    result = generate_ai_coach_output(_sample_context(), child_question="What should I practice?")
    assert result["used_fallback"] is False
    assert result["confidence"] == 0.88
    assert result["suggested_skill_tag"] == "inference"
    assert captured["kwargs"]["response_format"] == {"type": "json_object"}


def test_invalid_schema_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chat(messages, **kwargs):
        return {"model": "openai/gpt-oss-120b", "response_text": "Not JSON at all"}

    monkeypatch.setattr(ai_coach, "run_openrouter_chat", fake_chat)
    result = generate_ai_coach_output(_sample_context(), child_question="How can I make the evidence stronger?")
    assert result["used_fallback"] is True
    assert result["message_to_child"]
    assert "evidence" in result["message_to_child"].lower()
    assert 0 <= result["confidence"] <= 1


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "ai-coach-api.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    with TestClient(app) as test_client:
        login = test_client.post("/api/auth/login", json={"username": "user", "password": "password"})
        assert login.status_code == 200
        submit = test_client.post(
            "/api/activities/nature-01/submit",
            json={
                "responses": [
                    {"question_id": "q1", "answer_choice": "The oak tree's roots took the water"},
                    {"question_id": "q2", "answer_choice": "Healthy things that help plants grow"},
                    {"question_id": "q3", "answer_choice": "Determined"},
                    {"question_id": "q4", "answer_text": "Lila did not give up because she tried moving the pot to a sunny spot."},
                ]
            },
        )
        assert submit.status_code == 200
        test_client._session_id = submit.json()["session_id"]  # type: ignore[attr-defined]
        yield test_client


def test_ai_coach_route_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_generate(context, child_question=None):
        return {
            "message_to_child": "Great effort today.",
            "message_to_parent": "Good progress this session.",
            "hint": "Use clue words.",
            "explanation": "Evidence makes answers stronger.",
            "celebration": "You completed your quest!",
            "suggested_next_activity_id": "river-map",
            "suggested_skill_tag": "inference",
            "writing_feedback": "Add one more sentence.",
            "confidence": 0.8,
            "used_fallback": False,
            "model": "openai/gpt-oss-120b",
        }

    monkeypatch.setattr("backend.app.main.generate_ai_coach_output", fake_generate)
    response = client.post(
        "/api/ai/coach",
        json={"session_id": client._session_id, "child_question": "Can I try another challenge?"},  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    assert response.json()["used_fallback"] is False
    assert response.json()["suggested_skill_tag"] == "inference"


def test_ai_coach_route_provider_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_generate(context, child_question=None):
        raise OpenRouterProviderError("provider failed")

    monkeypatch.setattr("backend.app.main.generate_ai_coach_output", fake_generate)
    response = client.post("/api/ai/coach", json={"session_id": client._session_id})  # type: ignore[attr-defined]
    assert response.status_code == 502


def test_ai_coach_route_missing_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_generate(context, child_question=None):
        raise MissingOpenRouterKeyError("OPENROUTER_API_KEY is not configured.")

    monkeypatch.setattr("backend.app.main.generate_ai_coach_output", fake_generate)
    response = client.post("/api/ai/coach", json={"session_id": client._session_id})  # type: ignore[attr-defined]
    assert response.status_code == 503
