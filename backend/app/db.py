import os
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


APP_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = APP_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "ela.sqlite3"


def get_database_path() -> Path:
    override = os.environ.get("DATABASE_PATH")
    if override:
        return Path(override)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or get_database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS child_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            grade_level INTEGER NOT NULL DEFAULT 3,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activity_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_uuid TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            child_profile_id INTEGER NOT NULL,
            activity_id TEXT NOT NULL,
            activity_title TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('started', 'submitted')),
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            submitted_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(child_profile_id) REFERENCES child_profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            question_type TEXT NOT NULL CHECK(question_type IN ('multiple-choice', 'short-response')),
            answer_text TEXT,
            answer_choice TEXT,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES activity_sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL UNIQUE,
            total_score REAL NOT NULL,
            max_score REAL NOT NULL,
            score_percent REAL NOT NULL,
            rubric_json TEXT NOT NULL DEFAULT '{}',
            skill_breakdown_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES activity_sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS progress_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            child_profile_id INTEGER NOT NULL,
            captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completion_count INTEGER NOT NULL DEFAULT 0,
            average_score_percent REAL NOT NULL DEFAULT 0,
            strengths_json TEXT NOT NULL DEFAULT '[]',
            growth_areas_json TEXT NOT NULL DEFAULT '[]',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(child_profile_id) REFERENCES child_profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reward_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            stars INTEGER NOT NULL DEFAULT 0,
            streak_days INTEGER NOT NULL DEFAULT 0,
            badges_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            child_profile_id INTEGER NOT NULL,
            session_id INTEGER,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(child_profile_id) REFERENCES child_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY(session_id) REFERENCES activity_sessions(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user ON activity_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_child ON activity_sessions(child_profile_id);
        CREATE INDEX IF NOT EXISTS idx_progress_child ON progress_snapshots(child_profile_id);
        CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id);
        """
    )
    connection.commit()


def seed_core_records(connection: sqlite3.Connection) -> dict[str, int]:
    connection.execute(
        "INSERT OR IGNORE INTO users (username) VALUES (?)",
        ("user",),
    )
    user_id = connection.execute("SELECT id FROM users WHERE username = ?", ("user",)).fetchone()["id"]

    connection.execute(
        """
        INSERT OR IGNORE INTO child_profiles (user_id, display_name, grade_level)
        VALUES (?, ?, ?)
        """,
        (user_id, "Explorer Kid", 3),
    )
    child_profile_id = connection.execute(
        "SELECT id FROM child_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()["id"]

    connection.execute(
        """
        INSERT OR IGNORE INTO reward_state (user_id, stars, streak_days, badges_json)
        VALUES (?, 0, 0, '[]')
        """,
        (user_id,),
    )
    connection.commit()
    return {"user_id": user_id, "child_profile_id": child_profile_id}


def ensure_database(db_path: Optional[Path] = None) -> Path:
    target = db_path or get_database_path()
    with get_connection(target) as connection:
        create_schema(connection)
        seed_core_records(connection)
    return target


def insert_demo_progress_records(connection: sqlite3.Connection, user_id: int, child_profile_id: int) -> dict[str, Any]:
    connection.execute(
        """
        INSERT INTO activity_sessions (
            session_uuid, user_id, child_profile_id, activity_id, activity_title, status, submitted_at, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, 'submitted', CURRENT_TIMESTAMP, ?)
        """,
        (
            "session-demo-001",
            user_id,
            child_profile_id,
            "forest-friends",
            "Forest Friends",
            '{"source":"demo"}',
        ),
    )
    session_id = connection.execute(
        "SELECT id FROM activity_sessions WHERE session_uuid = ?",
        ("session-demo-001",),
    ).fetchone()["id"]

    connection.execute(
        """
        INSERT INTO responses (session_id, question_id, question_type, answer_choice, evidence_json)
        VALUES (?, 'q1', 'multiple-choice', ?, '{}')
        """,
        (session_id, "The birds show teamwork while building a nest."),
    )
    connection.execute(
        """
        INSERT INTO responses (session_id, question_id, question_type, answer_text, evidence_json)
        VALUES (?, 'q2', 'short-response', ?, ?)
        """,
        (
            session_id,
            "The bird flew back for the twig after the wind knocked it down.",
            '{"mentions_evidence": true}',
        ),
    )
    connection.execute(
        """
        INSERT INTO scores (session_id, total_score, max_score, score_percent, rubric_json, skill_breakdown_json)
        VALUES (?, 4, 5, 80, ?, ?)
        """,
        (
            session_id,
            '{"completion":"meets","relevance":"meets","sentence_completeness":"meets","skill_specific_checks":["evidence reference"]}',
            '{"inference":80,"short-writing":80}',
        ),
    )
    connection.execute(
        """
        INSERT INTO progress_snapshots (
            user_id, child_profile_id, completion_count, average_score_percent, strengths_json, growth_areas_json
        )
        VALUES (?, ?, 1, 80, ?, ?)
        """,
        (user_id, child_profile_id, '["inference"]', '["sentence-quality"]'),
    )
    connection.execute(
        """
        UPDATE reward_state
        SET stars = 3, streak_days = 1, badges_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        ('["Story Explorer"]', user_id),
    )
    connection.execute(
        """
        INSERT INTO chat_messages (user_id, child_profile_id, session_id, role, content, metadata_json)
        VALUES (?, ?, ?, 'assistant', ?, ?)
        """,
        (
            user_id,
            child_profile_id,
            session_id,
            "Great job using evidence from the story.",
            '{"kind":"post_submission_coach"}',
        ),
    )
    connection.commit()
    return {"session_id": session_id}


def fetch_dashboard_projection(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT
            u.username,
            rs.stars,
            rs.streak_days,
            COALESCE(ps.completion_count, 0) AS completion_count,
            COALESCE(ps.average_score_percent, 0) AS average_score_percent
        FROM users u
        LEFT JOIN reward_state rs ON rs.user_id = u.id
        LEFT JOIN progress_snapshots ps
            ON ps.id = (
                SELECT id
                FROM progress_snapshots
                WHERE user_id = u.id
                ORDER BY captured_at DESC, id DESC
                LIMIT 1
            )
        WHERE u.id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise ValueError("User not found for dashboard projection.")
    return row


def fetch_parent_progress_projection(connection: sqlite3.Connection, child_profile_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT
            cp.display_name,
            cp.grade_level,
            COUNT(DISTINCT s.id) AS session_count,
            COALESCE(AVG(sc.score_percent), 0) AS avg_score_percent,
            MAX(s.submitted_at) AS last_submitted_at
        FROM child_profiles cp
        LEFT JOIN activity_sessions s ON s.child_profile_id = cp.id
        LEFT JOIN scores sc ON sc.session_id = s.id
        WHERE cp.id = ?
        GROUP BY cp.id
        """,
        (child_profile_id,),
    ).fetchone()
    if row is None:
        raise ValueError("Child profile not found for progress projection.")
    return row


def get_user_by_username(connection: sqlite3.Connection, username: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT id, username FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        raise ValueError(f'Unknown user "{username}".')
    return row


def get_child_profile_for_user(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = connection.execute(
        "SELECT id, display_name, grade_level FROM child_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Child profile missing for user_id={user_id}.")
    return row


def get_reward_state(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = connection.execute(
        "SELECT stars, streak_days, badges_json, updated_at FROM reward_state WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Reward state missing for user_id={user_id}.")
    return row


def get_latest_progress_snapshot(
    connection: sqlite3.Connection, user_id: int, child_profile_id: int
) -> Optional[sqlite3.Row]:
    return connection.execute(
        """
        SELECT completion_count, average_score_percent, strengths_json, growth_areas_json
        FROM progress_snapshots
        WHERE user_id = ? AND child_profile_id = ?
        ORDER BY captured_at DESC, id DESC
        LIMIT 1
        """,
        (user_id, child_profile_id),
    ).fetchone()


def get_recent_sessions(connection: sqlite3.Connection, child_profile_id: int, limit: int = 5) -> list[sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT s.session_uuid, s.activity_id, s.activity_title, s.submitted_at, sc.score_percent
        FROM activity_sessions s
        LEFT JOIN scores sc ON sc.session_id = s.id
        WHERE s.child_profile_id = ? AND s.status = 'submitted'
        ORDER BY s.submitted_at DESC, s.id DESC
        LIMIT ?
        """,
        (child_profile_id, limit),
    ).fetchall()
    return list(rows)


def get_recent_score_history(connection: sqlite3.Connection, child_profile_id: int, limit: int = 5) -> list[float]:
    rows = connection.execute(
        """
        SELECT sc.score_percent
        FROM activity_sessions s
        JOIN scores sc ON sc.session_id = s.id
        WHERE s.child_profile_id = ? AND s.status = 'submitted'
        ORDER BY s.submitted_at DESC, s.id DESC
        LIMIT ?
        """,
        (child_profile_id, limit),
    ).fetchall()
    return [float(row["score_percent"]) for row in rows]


def compute_historical_skill_summary(
    connection: sqlite3.Connection, child_profile_id: int, limit: int = 10
) -> tuple[list[str], list[str]]:
    """Compute strengths and growth areas from recent session history.

    Aggregates per-skill-tag averages across the last N submitted sessions.
    Tags with average score >= 75 are strengths; < 75 are growth areas.
    """
    rows = connection.execute(
        """
        SELECT sc.skill_breakdown_json, sc.score_percent
        FROM activity_sessions s
        JOIN scores sc ON sc.session_id = s.id
        WHERE s.child_profile_id = ? AND s.status = 'submitted'
        ORDER BY s.submitted_at DESC, s.id DESC
        LIMIT ?
        """,
        (child_profile_id, limit),
    ).fetchall()

    if not rows:
        return [], []

    tag_scores: dict[str, list[float]] = {}
    for row in rows:
        breakdown = json.loads(row["skill_breakdown_json"]) if row["skill_breakdown_json"] else {}
        for tag, value in breakdown.items():
            tag_scores.setdefault(tag, []).append(float(value))

    strengths = sorted(tag for tag, scores in tag_scores.items() if sum(scores) / len(scores) >= 75)
    growth_areas = sorted(tag for tag, scores in tag_scores.items() if sum(scores) / len(scores) < 75)
    return strengths, growth_areas


def get_recent_writing_feedback(
    connection: sqlite3.Connection, child_profile_id: int, limit: int = 3
) -> list[dict[str, str]]:
    rows = connection.execute(
        """
        SELECT s.activity_title, sc.rubric_json
        FROM activity_sessions s
        JOIN scores sc ON sc.session_id = s.id
        WHERE s.child_profile_id = ? AND s.status = 'submitted'
        ORDER BY s.submitted_at DESC, s.id DESC
        LIMIT ?
        """,
        (child_profile_id, limit),
    ).fetchall()

    feedback_items: list[dict[str, str]] = []
    for row in rows:
        rubric = json.loads(row["rubric_json"]) if row["rubric_json"] else {}
        completion = rubric.get("completion", "unknown")
        relevance = rubric.get("relevance", "unknown")
        sentence = rubric.get("sentence_completeness", "unknown")
        checks = rubric.get("skill_specific_checks", [])
        checks_text = ", ".join(checks) if isinstance(checks, list) and checks else "none yet"
        summary = (
            f"Completion: {completion}; Relevance: {relevance}; "
            f"Sentence completeness: {sentence}; Skill checks: {checks_text}."
        )
        feedback_items.append({"activity_title": row["activity_title"], "summary": summary})

    return feedback_items


def create_submission(
    connection: sqlite3.Connection,
    user_id: int,
    child_profile_id: int,
    activity_id: str,
    activity_title: str,
    responses: list[dict[str, Any]],
    scoring_payload: dict[str, Any],
) -> dict[str, Any]:
    session_uuid = str(uuid.uuid4())
    connection.execute(
        """
        INSERT INTO activity_sessions (
            session_uuid, user_id, child_profile_id, activity_id, activity_title, status, submitted_at, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, 'submitted', CURRENT_TIMESTAMP, ?)
        """,
        (session_uuid, user_id, child_profile_id, activity_id, activity_title, "{}"),
    )
    session_id = connection.execute(
        "SELECT id FROM activity_sessions WHERE session_uuid = ?",
        (session_uuid,),
    ).fetchone()["id"]

    for response in responses:
        connection.execute(
            """
            INSERT INTO responses (session_id, question_id, question_type, answer_text, answer_choice, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                response["question_id"],
                response["question_type"],
                response.get("answer_text"),
                response.get("answer_choice"),
                json.dumps({}),
            ),
        )

    connection.execute(
        """
        INSERT INTO scores (session_id, total_score, max_score, score_percent, rubric_json, skill_breakdown_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            scoring_payload["total_score"],
            scoring_payload["max_score"],
            scoring_payload["score_percent"],
            json.dumps(scoring_payload["rubric"]),
            json.dumps(scoring_payload["skill_breakdown"]),
        ),
    )

    previous = get_latest_progress_snapshot(connection, user_id, child_profile_id)
    previous_completion = int(previous["completion_count"]) if previous else 0
    previous_avg = float(previous["average_score_percent"]) if previous else 0.0
    next_completion = previous_completion + 1
    next_avg = ((previous_avg * previous_completion) + float(scoring_payload["score_percent"])) / next_completion

    strengths, growth_areas = compute_historical_skill_summary(connection, child_profile_id)

    connection.execute(
        """
        INSERT INTO progress_snapshots (
            user_id, child_profile_id, completion_count, average_score_percent, strengths_json, growth_areas_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            child_profile_id,
            next_completion,
            round(next_avg, 2),
            json.dumps(strengths),
            json.dumps(growth_areas),
        ),
    )

    reward_row = get_reward_state(connection, user_id)
    previous_stars = int(reward_row["stars"])
    previous_streak = int(reward_row["streak_days"])
    stars_earned = int(round(scoring_payload["score_percent"] / 25))
    stars = previous_stars + stars_earned

    from datetime import date, datetime

    today = date.today()
    last_updated = reward_row["updated_at"]
    if last_updated:
        last_date = datetime.fromisoformat(last_updated.replace("Z", "+00:00")).date() if "T" in last_updated else datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S").date()
        days_gap = (today - last_date).days
        if days_gap == 0:
            streak_days = previous_streak
        elif days_gap == 1:
            streak_days = previous_streak + 1
        else:
            streak_days = 1
    else:
        streak_days = 1
    badges = json.loads(reward_row["badges_json"])
    previous_badges = set(badges)
    if next_completion >= 3 and "Three Mission Starter" not in badges:
        badges.append("Three Mission Starter")

    connection.execute(
        """
        UPDATE reward_state
        SET stars = ?, streak_days = ?, badges_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (stars, streak_days, json.dumps(badges), user_id),
    )

    reward_snapshot = {
        "stars_before": previous_stars,
        "stars_after": stars,
        "stars_earned": stars_earned,
        "streak_before": previous_streak,
        "streak_after": streak_days,
        "badges_before": sorted(previous_badges),
        "badges_after": badges,
        "new_badges": [badge for badge in badges if badge not in previous_badges],
        "points_earned": stars_earned * 10,
        "total_points": stars * 10,
    }
    connection.execute(
        "UPDATE activity_sessions SET metadata_json = ? WHERE id = ?",
        (json.dumps({"reward_snapshot": reward_snapshot}), session_id),
    )

    connection.commit()
    return {"session_id": session_id, "session_uuid": session_uuid, "reward_snapshot": reward_snapshot}


def fetch_session_result_by_uuid(connection: sqlite3.Connection, session_uuid: str) -> Optional[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            s.id,
            s.session_uuid,
            s.user_id,
            s.child_profile_id,
            s.activity_id,
            s.activity_title,
            s.submitted_at,
            sc.total_score,
            sc.max_score,
            sc.score_percent,
            sc.rubric_json,
            sc.skill_breakdown_json,
            s.metadata_json
        FROM activity_sessions s
        JOIN scores sc ON sc.session_id = s.id
        WHERE s.session_uuid = ?
        LIMIT 1
        """,
        (session_uuid,),
    ).fetchone()


def get_session_responses(connection: sqlite3.Connection, session_id: int) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT question_id, question_type, answer_text, answer_choice
            FROM responses
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
    )


def insert_chat_message(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    child_profile_id: int,
    session_id: Optional[int],
    role: str,
    content: str,
    metadata: Dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO chat_messages (user_id, child_profile_id, session_id, role, content, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            child_profile_id,
            session_id,
            role,
            content,
            json.dumps(metadata),
        ),
    )
    connection.commit()
