from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from backend.app.db import (
    ensure_database,
    get_child_profile_for_user,
    get_connection,
    get_user_by_username,
)
from backend.app.main import app
from backend.app.skill_progress import (
    PILOT_ACTIVITY_IDS,
    build_adaptive_recommendation,
    classify_skill_evidence,
    compute_skill_windows,
    recommend_practice_next,
)
from backend.app.content_schema import list_seed_activities


def _insert_scored_session(
    connection,
    *,
    user_id: int,
    child_profile_id: int,
    submitted_at_utc: str,
    skill_breakdown: dict,
    score_percent: float,
    uuid: str,
) -> None:
    connection.execute(
        """
        INSERT INTO activity_sessions (
            session_uuid, user_id, child_profile_id, activity_id, activity_title,
            status, submitted_at, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, 'submitted', ?, '{}')
        """,
        (uuid, user_id, child_profile_id, "act", "Activity", submitted_at_utc),
    )
    session_id = connection.execute(
        "SELECT id FROM activity_sessions WHERE session_uuid = ?", (uuid,)
    ).fetchone()["id"]
    connection.execute(
        """
        INSERT INTO scores (session_id, total_score, max_score, score_percent, rubric_json, skill_breakdown_json)
        VALUES (?, ?, ?, ?, '{}', ?)
        """,
        (session_id, score_percent, 100.0, score_percent, _to_json(skill_breakdown)),
    )
    connection.commit()


def _to_json(payload) -> str:
    import json as _json

    return _json.dumps(payload)


@pytest.fixture
def seeded_child(tmp_path: Path):
    db_path = tmp_path / "skill-progress.sqlite3"
    ensure_database(db_path)
    with get_connection(db_path) as connection:
        user = get_user_by_username(connection, "user")
        child = get_child_profile_for_user(connection, int(user["id"]))
    return db_path, int(user["id"]), int(child["id"])


def test_compute_skill_windows_empty_returns_empty_buckets(seeded_child) -> None:
    db_path, _, child_id = seeded_child
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    with get_connection(db_path) as connection:
        windows = compute_skill_windows(
            connection, child_id, tz=ZoneInfo("UTC"), now=now
        )
    assert windows == {"7_day": {}, "30_day": {}, "all_time": {}}


def test_compute_skill_windows_aggregates_per_skill(seeded_child) -> None:
    db_path, user_id, child_id = seeded_child
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)

    with get_connection(db_path) as connection:
        # Today: inference 90, summary 80.
        _insert_scored_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-05-14 10:00:00",
            skill_breakdown={"inference": 90, "summary": 80},
            score_percent=85,
            uuid="s-today",
        )
        # Five days ago (inside 7-day window): inference 70.
        _insert_scored_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-05-09 10:00:00",
            skill_breakdown={"inference": 70},
            score_percent=70,
            uuid="s-5d",
        )
        # 20 days ago (outside 7-day window, inside 30-day): summary 50.
        _insert_scored_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-04-24 10:00:00",
            skill_breakdown={"summary": 50},
            score_percent=50,
            uuid="s-20d",
        )
        # 60 days ago (outside 30-day, all_time only): inference 40.
        _insert_scored_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-03-15 10:00:00",
            skill_breakdown={"inference": 40},
            score_percent=40,
            uuid="s-60d",
        )

        windows = compute_skill_windows(
            connection, child_id, tz=ZoneInfo("UTC"), now=now
        )

    seven = windows["7_day"]
    thirty = windows["30_day"]
    alltime = windows["all_time"]

    assert seven["inference"] == {"attempts": 2, "avg_score": 80.0}
    assert seven["summary"] == {"attempts": 1, "avg_score": 80.0}

    assert thirty["inference"] == {"attempts": 2, "avg_score": 80.0}
    assert thirty["summary"] == {"attempts": 2, "avg_score": 65.0}

    assert alltime["inference"] == {"attempts": 3, "avg_score": round((90 + 70 + 40) / 3, 2)}
    assert alltime["summary"] == {"attempts": 2, "avg_score": 65.0}


def test_recommend_practice_next_returns_lowest_with_enough_attempts() -> None:
    windows = {
        "30_day": {
            "inference": {"attempts": 3, "avg_score": 90.0},
            "summary": {"attempts": 4, "avg_score": 60.0},
            "vocabulary": {"attempts": 1, "avg_score": 30.0},  # below min_attempts
            "sentence-quality": {"attempts": 2, "avg_score": 70.0},
        }
    }
    recs = recommend_practice_next(windows, min_attempts=2, max_results=2)

    assert [r["skill"] for r in recs] == ["summary", "sentence-quality"]
    assert recs[0]["avg_score"] == 60.0
    assert recs[0]["attempts"] == 4


def test_recommend_practice_next_handles_empty_window() -> None:
    assert recommend_practice_next({"30_day": {}}) == []
    assert recommend_practice_next({}) == []


def test_recommend_practice_next_respects_ceiling() -> None:
    windows = {
        "30_day": {
            "inference": {"attempts": 5, "avg_score": 95.0},
            "summary": {"attempts": 5, "avg_score": 85.0},
        }
    }
    # With ceiling = 90, only summary remains.
    recs = recommend_practice_next(windows, score_ceiling=90.0)
    assert [r["skill"] for r in recs] == ["summary"]


@pytest.mark.parametrize(
    ("attempts", "average", "decision", "difficulty"),
    [
        (0, None, "gather-evidence", "medium"),
        (2, 100.0, "gather-evidence", "medium"),
        (3, 59.9, "step-down", "easy"),
        (3, 60.0, "hold", "medium"),
        (3, 85.0, "hold", "medium"),
        (3, 85.1, "step-up", "difficult"),
    ],
)
def test_adaptive_thresholds_are_explicit(
    attempts: int,
    average: Optional[float],
    decision: str,
    difficulty: str,
) -> None:
    result = classify_skill_evidence(attempts, average)
    assert result["decision"] == decision
    assert result["target_difficulty"] == difficulty


def test_adaptive_recommendation_completes_baseline_in_order() -> None:
    recommendation = build_adaptive_recommendation(
        {}, list_seed_activities(), {PILOT_ACTIVITY_IDS[0]}
    )
    assert recommendation["phase"] == "baseline"
    assert recommendation["activity_id"] == PILOT_ACTIVITY_IDS[1]
    assert recommendation["decision"] == "complete-baseline"


def test_adaptive_recommendation_explains_step_down() -> None:
    windows = {
        "30_day": {
            "main-idea": {"attempts": 3, "avg_score": 90.0},
            "vocabulary": {"attempts": 3, "avg_score": 90.0},
            "inference": {"attempts": 4, "avg_score": 55.0},
            "reading-comprehension": {"attempts": 3, "avg_score": 80.0},
            "summary": {"attempts": 3, "avg_score": 80.0},
        }
    }
    recommendation = build_adaptive_recommendation(
        windows, list_seed_activities(), set(PILOT_ACTIVITY_IDS)
    )
    assert recommendation["phase"] == "adaptive"
    assert recommendation["target_skill"] == "inference"
    assert recommendation["decision"] == "step-down"
    assert recommendation["difficulty"] == "easy"
    assert "below the 60%" in str(recommendation["reason"])


def test_adaptive_recommendation_excludes_tagged_draft_content() -> None:
    activities = list(list_seed_activities())
    statuses = {activity.id: "draft" for activity in activities}
    windows = {
        "30_day": {
            "main-idea": {"attempts": 4, "avg_score": 55.0},
            "vocabulary": {"attempts": 3, "avg_score": 80.0},
            "inference": {"attempts": 3, "avg_score": 80.0},
            "reading-comprehension": {"attempts": 3, "avg_score": 80.0},
            "summary": {"attempts": 3, "avg_score": 80.0},
        }
    }

    recommendation = build_adaptive_recommendation(
        windows,
        activities,
        set(PILOT_ACTIVITY_IDS),
        review_statuses=statuses,
    )

    assert recommendation["phase"] == "adaptive"
    assert recommendation["target_skill"] == "main-idea"
    assert recommendation["activity_id"] is None


def test_pilot_submission_creates_question_level_observations() -> None:
    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200
        response = client.post(
            "/api/activities/pilot-mystery-cat-01/submit",
            json={
                "responses": [
                    {
                        "question_id": "q1",
                        "answer_choice": "Pixel's cushion is empty and the ribbon resembles the bookmark's tassel.",
                    },
                    {
                        "question_id": "q2",
                        "answer_choice": "She compares where the paw prints and ribbon were found.",
                    },
                    {"question_id": "q3", "answer_choice": "Certain that an idea is true"},
                    {
                        "question_id": "q4",
                        "answer_text": "Mateo learns that every clue must fit because his first guess was wrong.",
                    },
                ]
            },
        )
        assert response.status_code == 200
        parent = client.get("/api/progress/parent").json()

    thirty_day = parent["skill_history"]["30_day"]
    assert thirty_day["reading-comprehension"]["attempts"] == 1
    assert thirty_day["inference"]["attempts"] == 1
    assert thirty_day["vocabulary"]["attempts"] == 1
    assert thirty_day["summary"]["attempts"] == 1


def test_parent_progress_recent_questions_includes_mc_correctness_no_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Use the autouse-fixture DB so the seed user + content registry are in
    # the same place the TestClient lifespan-created DB will live.
    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200

        submit = client.post(
            "/api/activities/nature-01/submit",
            json={
                "responses": [
                    {"question_id": "q1", "answer_choice": "The oak tree's roots took the water"},
                    {"question_id": "q2", "answer_choice": "wrong on purpose"},
                    {"question_id": "q3", "answer_choice": "Determined"},
                    {
                        "question_id": "q4",
                        "answer_text": "A short response that should not be echoed back.",
                    },
                ]
            },
        )
        assert submit.status_code == 200

        response = client.get("/api/progress/parent")

    assert response.status_code == 200
    body = response.json()
    assert "recent_questions" in body
    recent = body["recent_questions"]
    assert len(recent) >= 4

    by_qid = {entry["question_id"]: entry for entry in recent if entry["activity_id"] == "nature-01"}
    assert {"q1", "q2", "q3", "q4"}.issubset(by_qid.keys())

    mc_entry = by_qid["q1"]
    assert mc_entry["question_type"] == "multiple-choice"
    assert mc_entry["is_correct"] is True
    assert mc_entry["child_answer"] == "The oak tree's roots took the water"
    assert mc_entry["correct_answer"] == "The oak tree's roots took the water"
    assert mc_entry["activity_title"]
    assert mc_entry["prompt"]
    assert isinstance(mc_entry["skill_tags"], list) and mc_entry["skill_tags"]

    wrong_mc = by_qid["q2"]
    assert wrong_mc["is_correct"] is False

    short = by_qid["q4"]
    assert short["question_type"] == "short-response"
    assert short["is_correct"] is None
    assert short["child_answer"] is None  # verbatim free-text is intentionally not echoed
    assert short["correct_answer"] is None


def test_parent_progress_recent_questions_empty_when_no_submissions() -> None:
    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200
        response = client.get("/api/progress/parent")

    assert response.status_code == 200
    assert response.json()["recent_questions"] == []


def test_parent_progress_endpoint_exposes_skill_history_and_practice_next(
    seeded_child,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path, user_id, child_id = seeded_child
    with get_connection(db_path) as connection:
        for offset, score in ((1, 60), (2, 50), (3, 55)):
            day = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
            _insert_scored_session(
                connection,
                user_id=user_id,
                child_profile_id=child_id,
                submitted_at_utc=f"{day} 10:00:00",
                skill_breakdown={"summary": score},
                score_percent=score,
                uuid=f"s-summary-{offset}",
            )
        for offset, score in ((1, 92), (2, 88)):
            day = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
            _insert_scored_session(
                connection,
                user_id=user_id,
                child_profile_id=child_id,
                submitted_at_utc=f"{day} 11:00:00",
                skill_breakdown={"inference": score},
                score_percent=score,
                uuid=f"s-inference-{offset}",
            )

    # Point the running app at the same DB file the fixture seeded.
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        )
        assert login.status_code == 200
        response = client.get("/api/progress/parent")

    assert response.status_code == 200
    body = response.json()
    assert "skill_history" in body
    assert "practice_next" in body

    history = body["skill_history"]
    assert set(history.keys()) == {"7_day", "30_day", "all_time"}

    practice = body["practice_next"]
    assert len(practice) >= 1
    skills = {entry["skill"] for entry in practice}
    assert "summary" in skills  # the lowest-average skill should be recommended
