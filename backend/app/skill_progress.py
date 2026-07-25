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

from backend.app.content_schema import ActivityModel

from backend.app.streak import _parse_sqlite_utc_timestamp

DEFAULT_WINDOWS = (("7_day", 7), ("30_day", 30), ("all_time", None))
PILOT_ACTIVITY_IDS = (
    "pilot-mystery-cat-01",
    "pilot-space-mars-01",
    "pilot-world-japan-01",
)
ADAPTIVE_SKILLS = (
    "main-idea",
    "vocabulary",
    "inference",
    "reading-comprehension",
    "summary",
)
DIFFICULTY_RANK = {"easy": 0, "medium": 1, "difficult": 2}


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
        SELECT s.id AS session_id,
               sc.skill_breakdown_json,
               s.submitted_at,
               r.evidence_json
        FROM activity_sessions s
        JOIN scores sc ON sc.session_id = s.id
        LEFT JOIN responses r ON r.session_id = s.id
        WHERE s.child_profile_id = ?
          AND s.status = 'submitted'
          AND s.submitted_at IS NOT NULL
        """,
        (child_profile_id,),
    ).fetchall()

    sessions: Dict[int, Dict[str, object]] = {}
    for row in rows:
        session = sessions.setdefault(
            int(row["session_id"]),
            {
                "submitted_at": row["submitted_at"],
                "skill_breakdown_json": row["skill_breakdown_json"],
                "observations": [],
            },
        )
        raw_evidence = row["evidence_json"]
        if not raw_evidence:
            continue
        try:
            evidence = json.loads(raw_evidence)
            skill = evidence.get("skill_tag")
            score = float(evidence.get("score_percent"))
        except (AttributeError, TypeError, ValueError):
            continue
        if isinstance(skill, str) and skill:
            session["observations"].append((skill, score))  # type: ignore[union-attr]

    accumulators: Dict[str, Dict[str, Dict[str, float]]] = {name: {} for name, _ in windows}
    for session in sessions.values():
        observations = session["observations"]
        if not observations:
            try:
                breakdown = json.loads(str(session["skill_breakdown_json"] or "{}"))
            except ValueError:
                breakdown = {}
            if isinstance(breakdown, dict):
                observations = list(breakdown.items())
        if not observations:
            continue
        submitted_utc = _parse_sqlite_utc_timestamp(str(session["submitted_at"]))
        for name, cutoff in cutoffs.items():
            if cutoff is not None and submitted_utc < cutoff:
                continue
            window_bucket = accumulators[name]
            for tag, value in observations:
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


def classify_skill_evidence(attempts: int, avg_score: Optional[float]) -> Dict[str, object]:
    """Apply the deliberately small, parent-readable adaptation rule."""
    if attempts < 3 or avg_score is None:
        return {
            "decision": "gather-evidence",
            "target_difficulty": "medium",
            "reason": f"We have {attempts} of 3 observations needed before changing difficulty.",
        }
    if avg_score < 60:
        return {
            "decision": "step-down",
            "target_difficulty": "easy",
            "reason": f"Recent accuracy is {round(avg_score)}%, below the 60% support threshold.",
        }
    if avg_score <= 85:
        return {
            "decision": "hold",
            "target_difficulty": "medium",
            "reason": f"Recent accuracy is {round(avg_score)}%, inside the 60–85% productive range.",
        }
    return {
        "decision": "step-up",
        "target_difficulty": "difficult",
        "reason": f"Recent accuracy is {round(avg_score)}%, above the 85% challenge threshold.",
    }


def build_adaptive_recommendation(
    skill_windows: Dict[str, Dict[str, Dict[str, float]]],
    activities: Iterable[ActivityModel],
    completed_activity_ids: Iterable[str],
    *,
    window: str = "30_day",
    review_statuses: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Return one recommendation plus the evidence and exact rule behind it.

    Only editorially reviewed activities whose questions all declare a primary
    skill are eligible. This prevents draft content from becoming targeted
    evidence merely because it happens to contain tags.
    """
    activity_list = list(activities)
    completed = set(completed_activity_ids)
    if review_statuses is None:
        from backend.app.content_schema import load_review_statuses

        review_statuses = load_review_statuses()
    by_id = {activity.id: activity for activity in activity_list}

    for activity_id in PILOT_ACTIVITY_IDS:
        if activity_id not in completed and activity_id in by_id:
            activity = by_id[activity_id]
            return {
                "phase": "baseline",
                "activity_id": activity.id,
                "activity_title": activity.title,
                "difficulty": activity.difficulty,
                "target_skill": None,
                "decision": "complete-baseline",
                "attempts": 0,
                "avg_score": None,
                "reason": "Complete the three starter missions before difficulty adapts.",
                "rule": "Starter missions run in order: cat mystery → Mars → Japan.",
            }

    bucket = skill_windows.get(window, {})
    states = []
    for skill in ADAPTIVE_SKILLS:
        stats = bucket.get(skill, {})
        attempts = int(stats.get("attempts", 0))
        avg_score = float(stats["avg_score"]) if "avg_score" in stats else None
        classification = classify_skill_evidence(attempts, avg_score)
        states.append(
            {
                "skill": skill,
                "attempts": attempts,
                "avg_score": avg_score,
                **classification,
            }
        )

    decision_priority = {"step-down": 0, "gather-evidence": 1, "hold": 2, "step-up": 3}
    states.sort(
        key=lambda item: (
            decision_priority[str(item["decision"])],
            item["attempts"],
            item["avg_score"] if item["avg_score"] is not None else -1,
            ADAPTIVE_SKILLS.index(str(item["skill"])),
        )
    )
    target = states[0]
    target_skill = str(target["skill"])
    target_difficulty = str(target["target_difficulty"])
    eligible = [
        activity
        for activity in activity_list
        if activity.questions
        and review_statuses.get(activity.id) == "reviewed"
        and all(question.skillTag is not None for question in activity.questions)
        and any(question.skillTag == target_skill for question in activity.questions)
    ]
    eligible.sort(
        key=lambda activity: (
            activity.id in completed,
            abs(DIFFICULTY_RANK[str(activity.difficulty)] - DIFFICULTY_RANK[target_difficulty]),
            activity.id,
        )
    )
    selected = eligible[0] if eligible else None
    return {
        "phase": "adaptive",
        "activity_id": selected.id if selected else None,
        "activity_title": selected.title if selected else None,
        "difficulty": selected.difficulty if selected else target_difficulty,
        "target_skill": target_skill,
        "decision": target["decision"],
        "attempts": target["attempts"],
        "avg_score": target["avg_score"],
        "reason": target["reason"],
        "rule": "<3 observations: gather evidence; <60%: easier; 60–85%: hold; >85%: harder.",
    }
