"""Streak math, derived from ``activity_sessions.submitted_at`` history.

Definitions:

- A *learning day* is any calendar day, in the configured local timezone,
  on which the child has at least one submitted activity.
- The *current streak* is the count of consecutive learning days ending
  on today (or yesterday — the streak is considered alive until the day
  after it is broken, so a child who studied yesterday still has their
  streak today).
- If the most recent learning day is older than yesterday, the streak is
  ``0``.

The previous implementation derived streak from ``reward_state.updated_at``
which is updated on every write — that conflated "time of last DB write"
with "time of last activity" and broke when submissions crossed day
boundaries or when the row was created without a real activity. This
module computes streak from the durable activity history instead.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo


def _parse_sqlite_utc_timestamp(raw: str) -> datetime:
    """SQLite ``CURRENT_TIMESTAMP`` returns ``'YYYY-MM-DD HH:MM:SS'`` in UTC.
    Some rows may be ISO-8601 with explicit zone (from earlier writers).
    Both forms are normalized to a timezone-aware UTC ``datetime``."""
    cleaned = raw.strip()
    if "T" in cleaned:
        # ISO-8601 form. Tolerate trailing 'Z'.
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def compute_streak(distinct_days_desc: List[date], today: date) -> int:
    """Return the streak ending at ``today``, allowing yesterday as an
    accepted starting point so a child who studied yesterday still sees
    their streak today before doing today's lesson.

    ``distinct_days_desc`` must be newest-first with no duplicates.
    """
    if not distinct_days_desc:
        return 0

    latest = distinct_days_desc[0]
    if latest == today:
        starting_point = today
    elif latest == today - timedelta(days=1):
        starting_point = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    expected = starting_point
    for day in distinct_days_desc:
        if day == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        elif day < expected:
            break
        # day > expected should not happen with a sorted list; ignore defensively
    return streak


def get_distinct_learning_days(
    connection: sqlite3.Connection,
    child_profile_id: int,
    tz: ZoneInfo,
) -> List[date]:
    """Read submission timestamps, convert to ``tz``, and return distinct
    calendar dates newest-first."""
    rows = connection.execute(
        """
        SELECT submitted_at
        FROM activity_sessions
        WHERE child_profile_id = ?
          AND status = 'submitted'
          AND submitted_at IS NOT NULL
        ORDER BY submitted_at DESC
        """,
        (child_profile_id,),
    ).fetchall()

    seen: set[date] = set()
    days: List[date] = []
    for row in rows:
        local = _parse_sqlite_utc_timestamp(row["submitted_at"]).astimezone(tz)
        day = local.date()
        if day in seen:
            continue
        seen.add(day)
        days.append(day)
    return days


def compute_streak_for_child(
    connection: sqlite3.Connection,
    child_profile_id: int,
    *,
    tz: ZoneInfo,
    today: Optional[date] = None,
) -> int:
    """Compute the child's current streak using sessions in the DB.

    ``today`` is overridable for tests; defaults to ``now()`` in ``tz``.
    """
    effective_today = today if today is not None else datetime.now(tz).date()
    days = get_distinct_learning_days(connection, child_profile_id, tz)
    return compute_streak(days, effective_today)
