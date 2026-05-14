"""Per-skill performance aggregation for the parent progress view.

The brief asked for time-windowed summaries (7 day / 30 day / all-time) and a
parent-facing "practice this next" pointer. Computation happens on read —
the data volume per child is tiny (hundreds of sessions at most for an MVP)
and recomputing on demand keeps the model explainable: "this is the average
of these scores", not a black-box mastery curve.

Windows are anchored on the configured ``learning_day_timezone`` so a session
submitted at 11pm Sunday local stays in Sunday's bucket regardless of UTC
offset.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from backend.app.streak import _parse_sqlite_utc_timestamp

DEFAULT_WINDOWS = (("7_day", 7), ("30_day", 30), ("all_time", None))


def _window_cutoffs_utc(
    now_utc: datetime,
    tz: ZoneInfo,
    windows: Iterable[tuple[str, Optional[int]]],
) -> Dict[str, Optional[datetime]]:
    """For each window length, return the UTC cutoff timestamp at/after which
    a session counts. ``all_time`` (length ``None``) maps to ``None``."""
    today_local = now_utc.astimezone(tz).date()
    cutoffs: Dict[str, Optional[datetime]] = {}
    for name, days in windows:
        if days is None:
            cutoffs[name] = None
            continue
        start_local = datetime.combine(today_local - timedelta(days=days - 1), time.min, tzinfo=tz)
        cutoffs[name] = start_local.astimezone(timezone.utc)
    return cutoffs


def compute_skill_windows(
    connection: sqlite3.Connection,
    child_profile_id: int,
    *,
    tz: ZoneInfo,
    now: Optional[datetime] = None,
    windows: Iterable[tuple[str, Optional[int]]] = DEFAULT_WINDOWS,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Aggregate per-skill attempts and average score across each window.

    Returns a dict keyed by window name; each value maps skill tag to
    ``{"attempts": int, "avg_score": float}``. Skills with zero attempts in
    a window are simply absent from that window's dict.
    """
    effective_now = now if now is not None else datetime.now(timezone.utc)
    if effective_now.tzinfo is None:
        effective_now = effective_now.replace(tzinfo=timezone.utc)
    cutoffs = _window_cutoffs_utc(effective_now, tz, windows)

    rows = connection.execute(
        """
        SELECT sc.skill_breakdown_json, s.submitted_at
        FROM activity_sessions s
        JOIN scores sc ON sc.session_id = s.id
        WHERE s.child_profile_id = ?
          AND s.status = 'submitted'
          AND s.submitted_at IS NOT NULL
        """,
        (child_profile_id,),
    ).fetchall()

    accumulators: Dict[str, Dict[str, Dict[str, float]]] = {name: {} for name, _ in windows}
    for row in rows:
        raw_breakdown = row["skill_breakdown_json"]
        if not raw_breakdown:
            continue
        try:
            breakdown = json.loads(raw_breakdown)
        except ValueError:
            continue
        if not isinstance(breakdown, dict) or not breakdown:
            continue
        submitted_utc = _parse_sqlite_utc_timestamp(row["submitted_at"])
        for name, cutoff in cutoffs.items():
            if cutoff is not None and submitted_utc < cutoff:
                continue
            window_bucket = accumulators[name]
            for tag, value in breakdown.items():
                try:
                    score = float(value)
                except (TypeError, ValueError):
                    continue
                stats = window_bucket.setdefault(tag, {"attempts": 0.0, "score_sum": 0.0})
                stats["attempts"] += 1
                stats["score_sum"] += score

    output: Dict[str, Dict[str, Dict[str, float]]] = {}
    for name in (n for n, _ in windows):
        output[name] = {
            tag: {
                "attempts": int(stats["attempts"]),
                "avg_score": round(stats["score_sum"] / stats["attempts"], 2),
            }
            for tag, stats in accumulators[name].items()
        }
    return output


def recommend_practice_next(
    skill_windows: Dict[str, Dict[str, Dict[str, float]]],
    *,
    window: str = "30_day",
    min_attempts: int = 2,
    max_results: int = 2,
    score_ceiling: float = 100.0,
) -> List[Dict[str, float]]:
    """Pick up to ``max_results`` skills in ``window`` with the lowest average
    score, requiring at least ``min_attempts`` attempts so single-session
    luck does not drive the suggestion. ``score_ceiling`` lets callers ignore
    already-mastered skills.
    """
    bucket = skill_windows.get(window, {})
    candidates = [
        {
            "skill": tag,
            "avg_score": float(stats["avg_score"]),
            "attempts": int(stats["attempts"]),
        }
        for tag, stats in bucket.items()
        if int(stats["attempts"]) >= min_attempts and float(stats["avg_score"]) <= score_ceiling
    ]
    candidates.sort(key=lambda entry: (entry["avg_score"], entry["skill"]))
    return candidates[:max_results]
