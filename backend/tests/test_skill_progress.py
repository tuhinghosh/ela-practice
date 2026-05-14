from datetime import datetime, timedelta, timezone
from pathlib import Path
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
    compute_skill_windows,
    recommend_practice_next,
)


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
