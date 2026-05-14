"""Streak math + DB-level integration tests."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.app.db import (
    create_submission,
    ensure_database,
    get_child_profile_for_user,
    get_connection,
    get_reward_state,
    get_user_by_username,
)
from backend.app.streak import (
    _parse_sqlite_utc_timestamp,
    compute_streak,
    compute_streak_for_child,
    get_distinct_learning_days,
)


def test_compute_streak_empty_history() -> None:
    assert compute_streak([], date(2026, 5, 14)) == 0


def test_compute_streak_today_only_is_one() -> None:
    today = date(2026, 5, 14)
    assert compute_streak([today], today) == 1


def test_compute_streak_yesterday_only_is_one() -> None:
    today = date(2026, 5, 14)
    yesterday = today - timedelta(days=1)
    assert compute_streak([yesterday], today) == 1


def test_compute_streak_two_days_ago_is_zero() -> None:
    today = date(2026, 5, 14)
    two_days_ago = today - timedelta(days=2)
    assert compute_streak([two_days_ago], today) == 0


def test_compute_streak_five_consecutive_days() -> None:
    today = date(2026, 5, 14)
    days = [today - timedelta(days=i) for i in range(5)]
    assert compute_streak(days, today) == 5


def test_compute_streak_gap_breaks_run() -> None:
    today = date(2026, 5, 14)
    days = [
        today,
        today - timedelta(days=1),
        # day -2 missing
        today - timedelta(days=3),
        today - timedelta(days=4),
    ]
    assert compute_streak(days, today) == 2


def test_compute_streak_yesterday_anchored_with_history() -> None:
    today = date(2026, 5, 14)
    days = [today - timedelta(days=i) for i in (1, 2, 3)]  # yesterday + two prior
    assert compute_streak(days, today) == 3


def test_parse_sqlite_utc_timestamp_default_form() -> None:
    parsed = _parse_sqlite_utc_timestamp("2026-05-14 03:30:00")
    assert parsed == datetime(2026, 5, 14, 3, 30, tzinfo=timezone.utc)


def test_parse_sqlite_utc_timestamp_iso_form_with_z() -> None:
    parsed = _parse_sqlite_utc_timestamp("2026-05-14T03:30:00Z")
    assert parsed == datetime(2026, 5, 14, 3, 30, tzinfo=timezone.utc)


def test_parse_sqlite_utc_timestamp_iso_form_with_offset() -> None:
    parsed = _parse_sqlite_utc_timestamp("2026-05-14T03:30:00+05:30")
    expected = datetime(2026, 5, 14, 3, 30, tzinfo=ZoneInfo("Asia/Kolkata")).astimezone(timezone.utc)
    assert parsed == expected


def _seed_session(
    connection,
    *,
    user_id: int,
    child_profile_id: int,
    submitted_at_utc: str,
    activity_id: str = "test-activity",
    uuid: str = "session-uuid-test",
) -> None:
    connection.execute(
        """
        INSERT INTO activity_sessions (
            session_uuid, user_id, child_profile_id, activity_id, activity_title,
            status, submitted_at, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, 'submitted', ?, '{}')
        """,
        (uuid, user_id, child_profile_id, activity_id, "Test", submitted_at_utc),
    )
    connection.commit()


@pytest.fixture
def seeded_child(tmp_path: Path):
    db_path = tmp_path / "streak.sqlite3"
    ensure_database(db_path)
    with get_connection(db_path) as connection:
        user = get_user_by_username(connection, "user")
        child = get_child_profile_for_user(connection, int(user["id"]))
    return db_path, int(user["id"]), int(child["id"])


def test_get_distinct_learning_days_dedupes_same_day(seeded_child) -> None:
    db_path, user_id, child_id = seeded_child
    with get_connection(db_path) as connection:
        _seed_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-05-14 09:00:00",
            uuid="s1",
        )
        _seed_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-05-14 17:00:00",
            uuid="s2",
        )
        _seed_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-05-13 12:00:00",
            uuid="s3",
        )

        days = get_distinct_learning_days(connection, child_id, ZoneInfo("UTC"))

    assert days == [date(2026, 5, 14), date(2026, 5, 13)]


def test_compute_streak_for_child_with_consecutive_days(seeded_child) -> None:
    db_path, user_id, child_id = seeded_child
    with get_connection(db_path) as connection:
        for offset in range(3):
            day = date(2026, 5, 14) - timedelta(days=offset)
            _seed_session(
                connection,
                user_id=user_id,
                child_profile_id=child_id,
                submitted_at_utc=f"{day.isoformat()} 12:00:00",
                uuid=f"s-{offset}",
            )

        streak = compute_streak_for_child(
            connection, child_id, tz=ZoneInfo("UTC"), today=date(2026, 5, 14)
        )

    assert streak == 3


def test_compute_streak_for_child_with_skipped_day(seeded_child) -> None:
    db_path, user_id, child_id = seeded_child
    with get_connection(db_path) as connection:
        for offset in (0, 1, 3):  # today, yesterday, day before previous (gap)
            day = date(2026, 5, 14) - timedelta(days=offset)
            _seed_session(
                connection,
                user_id=user_id,
                child_profile_id=child_id,
                submitted_at_utc=f"{day.isoformat()} 12:00:00",
                uuid=f"s-{offset}",
            )

        streak = compute_streak_for_child(
            connection, child_id, tz=ZoneInfo("UTC"), today=date(2026, 5, 14)
        )

    assert streak == 2


def test_compute_streak_for_child_respects_timezone(seeded_child) -> None:
    """A submission at 06:00 UTC on May 14 is May 13 in US/Pacific.
    With today = May 13 PT and history containing only that submission,
    streak should be 1 in PT (today) — and the same submission viewed in
    UTC for today=May 14 UTC should also be 1."""
    db_path, user_id, child_id = seeded_child
    with get_connection(db_path) as connection:
        _seed_session(
            connection,
            user_id=user_id,
            child_profile_id=child_id,
            submitted_at_utc="2026-05-14 06:00:00",
            uuid="cross-midnight",
        )

        utc_streak = compute_streak_for_child(
            connection, child_id, tz=ZoneInfo("UTC"), today=date(2026, 5, 14)
        )
        pt_streak = compute_streak_for_child(
            connection,
            child_id,
            tz=ZoneInfo("America/Los_Angeles"),
            today=date(2026, 5, 13),
        )

    assert utc_streak == 1
    assert pt_streak == 1


def test_create_submission_same_day_does_not_increment_streak(seeded_child) -> None:
    """Two real submissions on the same day produce streak=1."""
    db_path, user_id, child_id = seeded_child
    scoring = {
        "total_score": 4,
        "max_score": 5,
        "score_percent": 80,
        "rubric": {},
        "skill_breakdown": {},
        "question_feedback": [],
    }
    responses = [
        {"question_id": "q1", "question_type": "multiple-choice", "answer_choice": "a", "answer_text": None},
    ]

    with get_connection(db_path) as connection:
        first = create_submission(
            connection, user_id, child_id, "test-act", "Test Act", responses, scoring
        )
        second = create_submission(
            connection, user_id, child_id, "test-act", "Test Act", responses, scoring
        )

    assert first["reward_snapshot"]["streak_after"] == 1
    assert second["reward_snapshot"]["streak_after"] == 1


def test_config_default_timezone_is_utc() -> None:
    from backend.app.config import load_settings

    settings = load_settings(env={})
    assert str(settings.learning_day_timezone) == "UTC"


def test_config_invalid_timezone_raises_config_error() -> None:
    from backend.app.config import ConfigError, load_settings

    with pytest.raises(ConfigError, match="not a recognized IANA timezone"):
        load_settings(env={"LEARNING_DAY_TIMEZONE": "Mars/Olympus_Mons"})


def test_config_accepts_iana_timezone() -> None:
    from backend.app.config import load_settings

    settings = load_settings(env={"LEARNING_DAY_TIMEZONE": "America/Los_Angeles"})
    assert str(settings.learning_day_timezone) == "America/Los_Angeles"
