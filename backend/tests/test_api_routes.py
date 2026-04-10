from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "api-test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200


def _forest_friends_payload() -> dict:
    return {
        "responses": [
            {
                "question_id": "q1",
                "answer_choice": "The birds show teamwork while building a nest.",
            },
            {
                "question_id": "q2",
                "answer_text": "The bird brought the twig back because it kept trying.",
            },
        ]
    }


def _bees_payload() -> dict:
    return {
        "responses": [
            {
                "question_id": "q1",
                "answer_choice": "Bees spread pollen from one flower to another.",
            },
            {
                "question_id": "q2",
                "answer_text": "Bees move pollen and help plants make seeds.",
            },
        ]
    }


def test_activity_and_progress_routes(client: TestClient) -> None:
    _login(client)

    rewards_before = client.get("/api/rewards")
    assert rewards_before.status_code == 200
    stars_before = rewards_before.json()["stars"]
    streak_before = rewards_before.json()["streak_days"]

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert "mission" in dashboard.json()

    activities = client.get("/api/activities")
    assert activities.status_code == 200
    assert len(activities.json()["themes"]) >= 5
    assert set(activities.json()["difficulties"]) == {"easy", "medium", "difficult"}
    activity_items = activities.json()["activities"]
    assert len(activity_items) >= 50
    assert {"easy", "medium", "difficult"}.issuperset({item["difficulty"] for item in activity_items})
    first_theme = activity_items[0]["theme"]
    themed = client.get(f"/api/activities?theme={first_theme}")
    assert themed.status_code == 200
    assert len(themed.json()["activities"]) >= 1
    assert all(item["theme"] == first_theme for item in themed.json()["activities"])
    medium = client.get("/api/activities?difficulty=medium")
    assert medium.status_code == 200
    assert len(medium.json()["activities"]) >= 1
    assert all(item["difficulty"] == "medium" for item in medium.json()["activities"])

    activity_id = activity_items[0]["id"]

    activity_detail = client.get(f"/api/activities/{activity_id}")
    assert activity_detail.status_code == 200
    assert activity_detail.json()["id"] == activity_id

    submit_result = client.post(f"/api/activities/{activity_id}/submit", json=_forest_friends_payload())
    assert submit_result.status_code == 200
    assert submit_result.json()["score_percent"] >= 0
    session_id = submit_result.json()["session_id"]
    assert submit_result.json()["reward_snapshot"]["stars_after"] >= stars_before
    assert submit_result.json()["reward_snapshot"]["streak_after"] == streak_before + 1

    session_result = client.get(f"/api/sessions/{session_id}")
    assert session_result.status_code == 200
    assert session_result.json()["session_id"] == session_id
    assert session_result.json()["score_percent"] >= 0
    assert session_result.json()["reward_snapshot"]["stars_after"] >= stars_before

    parent = client.get("/api/progress/parent")
    assert parent.status_code == 200
    assert parent.json()["summary"]["session_count"] >= 1
    assert parent.json()["summary"]["skill_summary"]["strength"] != ""
    assert parent.json()["summary"]["skill_summary"]["struggle"] != ""
    assert parent.json()["summary"]["trend"] in {"starting", "improving", "steady", "needs-support"}
    assert isinstance(parent.json()["writing_feedback_summaries"], list)

    rewards = client.get("/api/rewards")
    assert rewards.status_code == 200
    assert "stars" in rewards.json()
    assert rewards.json()["stars"] >= stars_before


def test_invalid_payload_returns_validation_error(client: TestClient) -> None:
    _login(client)

    response = client.post(
        "/api/activities/forest-friends/submit",
        json={"responses": [{"question_id": "q1"}]},
    )
    assert response.status_code == 422

    unknown_question = client.post(
        "/api/activities/forest-friends/submit",
        json={
            "responses": [
                {"question_id": "unknown-q", "answer_choice": "anything"},
            ]
        },
    )
    assert unknown_question.status_code == 422

    bad_theme = client.get("/api/activities?theme=not-a-theme")
    assert bad_theme.status_code == 422
    bad_difficulty = client.get("/api/activities?difficulty=very-hard")
    assert bad_difficulty.status_code == 422


def test_repeat_submissions_are_predictable(client: TestClient) -> None:
    _login(client)
    rewards_start = client.get("/api/rewards").json()
    start_streak = rewards_start["streak_days"]
    payload = _bees_payload()

    first = client.post("/api/activities/bees-and-flowers/submit", json=payload)
    second = client.post("/api/activities/bees-and-flowers/submit", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["score_percent"] == second.json()["score_percent"]
    assert first.json()["session_id"] != second.json()["session_id"]
    assert second.json()["reward_snapshot"]["streak_after"] == first.json()["reward_snapshot"]["streak_after"] + 1

    rewards_end = client.get("/api/rewards").json()
    assert rewards_end["streak_days"] == start_streak + 2


def test_empty_state_for_new_profile(client: TestClient) -> None:
    _login(client)
    parent = client.get("/api/progress/parent")
    assert parent.status_code == 200
    assert parent.json()["summary"]["session_count"] == 0
    assert parent.json()["recent_sessions"] == []
    assert parent.json()["summary"]["trend"] == "starting"
    assert parent.json()["writing_feedback_summaries"] == []


def test_refresh_persistence_across_clients(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "refresh-test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    with TestClient(app) as first_client:
        _login(first_client)
        submit = first_client.post("/api/activities/forest-friends/submit", json=_forest_friends_payload())
        assert submit.status_code == 200
        first_session_id = submit.json()["session_id"]

    with TestClient(app) as second_client:
        _login(second_client)
        dashboard = second_client.get("/api/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["progress"]["completion_count"] >= 1

        parent = second_client.get("/api/progress/parent")
        assert parent.status_code == 200
        assert parent.json()["summary"]["session_count"] >= 1

        session_result = second_client.get(f"/api/sessions/{first_session_id}")
        assert session_result.status_code == 200
