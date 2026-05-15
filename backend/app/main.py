import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from backend.app.ai_client import (
    MissingOpenRouterKeyError,
    OpenRouterProviderError,
    OpenRouterTimeoutError,
    run_openrouter_connectivity_check,
)
from backend.app.ai_coach import generate_ai_coach_output
from backend.app.ai_quota import DailyAICallQuota, SQLiteQuotaStore
from backend.app.auth import hash_password, verify_password
from backend.app.config import get_settings
from backend.app.csrf import CSRFOriginMiddleware
from backend.app.logging_config import configure_logging
from backend.app.rate_limit import SlidingWindowLimiter
from backend.app.request_logging import RequestLoggingMiddleware
from backend.app.skill_progress import compute_skill_windows, recommend_practice_next
from backend.app.content_schema import (
    get_seed_activity,
    list_seed_activities,
    list_seed_difficulty_tiers,
    list_seed_themes,
    verify_content_manifest,
)
from backend.app.db import ensure_database
from backend.app.db import (
    create_submission,
    fetch_parent_progress_projection,
    fetch_session_result_by_uuid,
    get_child_profile_for_user,
    get_connection,
    get_latest_progress_snapshot,
    get_recent_responses_with_activity,
    get_recent_score_history,
    get_recent_sessions,
    get_recent_writing_feedback,
    get_reward_state,
    get_session_responses,
    get_user_by_username,
    insert_chat_message,
    update_user_password,
)
from backend.app.scoring import score_activity_submission


APP_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = APP_ROOT / "static"
settings = get_settings()
configure_logging(settings.log_level)
login_limiter = SlidingWindowLimiter(
    max_attempts=settings.login_rate_limit_max_attempts,
    window_seconds=settings.login_rate_limit_window_seconds,
)
ai_quota = DailyAICallQuota(
    daily_limit=settings.ai_calls_per_user_per_day,
    store=SQLiteQuotaStore(get_connection),
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_database()
    yield


app = FastAPI(title="ELA MVP API", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CSRFOriginMiddleware,
    allowed_origins=settings.csrf_allowed_origins,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie=settings.session_cookie_name,
    same_site=settings.session_cookie_samesite,
    https_only=settings.session_cookie_secure,
)

PROTECTED_ROUTE_PREFIXES = ("", "activity", "results", "parent")
PUBLIC_ROUTE_PREFIXES = ("login", "_next", "favicon.ico")


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=256)


class ChildAccountCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    grade_level: int = Field(default=3, ge=1, le=12)
    username: Optional[str] = Field(default=None, max_length=64)
    password: Optional[str] = Field(default=None, max_length=256)


class SubmissionAnswer(BaseModel):
    question_id: str = Field(min_length=1)
    answer_choice: Optional[str] = None
    answer_text: Optional[str] = None


class SubmitActivityRequest(BaseModel):
    responses: list[SubmissionAnswer] = Field(min_length=1)


class ConnectivityCheckRequest(BaseModel):
    prompt: str = "2+2"


class AICoachRequest(BaseModel):
    session_id: str = Field(min_length=1)
    child_question: Optional[str] = None


@app.get("/api/health")
def health() -> JSONResponse:
    """Liveness check — returns 200 as long as the process is up."""
    return JSONResponse({"status": "ok"})


@app.get("/api/ready")
def ready() -> JSONResponse:
    """Readiness check — confirms the database is reachable and migrated."""
    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM schema_migrations"
            ).fetchone()
        return JSONResponse({"status": "ok", "migrations_applied": int(row["n"])})
    except Exception as exc:  # pragma: no cover - exercised via simulated failure
        return JSONResponse(
            {"status": "unavailable", "error": str(exc)[:200]},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@app.get("/api/auth/session")
def auth_session(request: Request) -> JSONResponse:
    is_authenticated = bool(request.session.get("authenticated"))
    username = request.session.get("username")
    role = request.session.get("role")
    return JSONResponse(
        {
            "authenticated": is_authenticated,
            "username": username if is_authenticated else None,
            "role": role if is_authenticated else None,
        }
    )


def _require_authenticated_username(request: Request) -> str:
    username = request.session.get("username")
    authenticated = request.session.get("authenticated")
    if not authenticated or not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return str(username)


def _require_authenticated_parent(request: Request) -> str:
    """Same as ``_require_authenticated_username`` but additionally enforces
    that the session's role is ``parent``. Returns the username on success."""
    username = _require_authenticated_username(request)
    role = request.session.get("role")
    if role != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Parent role required for this action.",
        )
    return username


def _require_authenticated_child(request: Request) -> str:
    """Same as ``_require_authenticated_username`` but additionally enforces
    that the session's role is ``child``. Returns the username on success."""
    username = _require_authenticated_username(request)
    role = request.session.get("role")
    if role != "child":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Child role required for this action.",
        )
    return username


def _resolve_active_child_or_400(connection, request: Request, user_row) -> dict:
    """Caller-friendly wrapper around ``_resolve_active_child_profile``: raises
    a 400 with a useful message when the caller has no resolvable child
    profile (e.g. a parent who soft-deleted their only child)."""
    profile = _resolve_active_child_profile(connection, request, user_row)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No active child profile available for this account. "
                "Create or activate a child profile to continue."
            ),
        )
    return profile


def _resolve_active_child_profile(
    connection,
    request: Request,
    user_row,
) -> Optional[dict]:
    """Pick the child_profiles row the caller is currently focused on.

    - **Child caller:** the unique profile where ``login_user_id`` matches
      the caller's user id (always unambiguous; the partial unique index
      from migration #3 enforces this).
    - **Parent caller:** the profile id stored in
      ``session["active_child_profile_id"]`` if it still belongs to the
      parent; otherwise the parent's first owned active child by id.
      Returns ``None`` when the parent owns no children.

    Returns a dict mapping or ``None`` so callers can branch on
    ``profile is None`` without sqlite3.Row truthiness surprises.
    """
    role = request.session.get("role")
    user_id = int(user_row["id"])
    if role == "child":
        row = connection.execute(
            """
            SELECT id, user_id, login_user_id, display_name, grade_level, is_active
            FROM child_profiles WHERE login_user_id = ? AND is_active = 1
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    # Parent path.
    requested = request.session.get("active_child_profile_id")
    if requested is not None:
        row = connection.execute(
            """
            SELECT id, user_id, login_user_id, display_name, grade_level, is_active
            FROM child_profiles
            WHERE id = ? AND user_id = ? AND is_active = 1
            """,
            (int(requested), user_id),
        ).fetchone()
        if row is not None:
            return dict(row)
        # Stale id; clear so subsequent calls don't keep re-checking it.
        request.session.pop("active_child_profile_id", None)

    row = connection.execute(
        """
        SELECT id, user_id, login_user_id, display_name, grade_level, is_active
        FROM child_profiles
        WHERE user_id = ? AND is_active = 1
        ORDER BY id
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_ai_quota(user_id: int) -> Optional[JSONResponse]:
    """Charge one AI call to the user's daily budget. Returns a 429 response
    when the limit is exceeded; otherwise returns ``None`` and the caller
    may proceed."""
    result = ai_quota.register(user_id)
    if not result.allowed:
        return JSONResponse(
            {
                "error": "Daily AI call limit reached.",
                "detail": f"You have used {result.used} of {result.limit} AI calls today.",
                "reset_at": result.reset_at.isoformat(),
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": "3600"},
        )
    return None


@app.post("/api/parent/child-accounts")
def create_child_account(
    payload: ChildAccountCreateRequest,
    username: str = Depends(_require_authenticated_parent),
) -> JSONResponse:
    """Parent creates a child profile, optionally backed by a child-role
    user row with its own login."""
    if (payload.username is None) != (payload.password is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide username and password together, or neither.",
        )
    child_username = payload.username.strip() if payload.username else None
    if child_username is not None:
        if len(child_username) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Child username must be at least 3 characters.",
            )
        if payload.password is None or len(payload.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Child password must be at least 8 characters.",
            )

    with get_connection() as connection:
        parent = get_user_by_username(connection, username)
        login_user_id: Optional[int] = None
        if child_username is not None:
            existing = connection.execute(
                "SELECT id FROM users WHERE username = ?", (child_username,)
            ).fetchone()
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f'Username "{child_username}" is already in use.',
                )
            password_hash = hash_password(payload.password)  # type: ignore[arg-type]
            connection.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'child')",
                (child_username, password_hash),
            )
            login_user_id = int(
                connection.execute(
                    "SELECT id FROM users WHERE username = ?", (child_username,)
                ).fetchone()["id"]
            )
            # Each user has a reward_state row keyed by user_id; seed it
            # so the dashboard works the first time the child logs in.
            connection.execute(
                "INSERT INTO reward_state (user_id, stars, streak_days, badges_json) "
                "VALUES (?, 0, 0, '[]')",
                (login_user_id,),
            )
        connection.execute(
            """
            INSERT INTO child_profiles (user_id, login_user_id, display_name, grade_level)
            VALUES (?, ?, ?, ?)
            """,
            (int(parent["id"]), login_user_id, payload.display_name, payload.grade_level),
        )
        connection.commit()
        new_profile = connection.execute(
            """
            SELECT id, user_id, login_user_id, display_name, grade_level, is_active
            FROM child_profiles
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(parent["id"]),),
        ).fetchone()

    return JSONResponse(
        {
            "id": int(new_profile["id"]),
            "display_name": new_profile["display_name"],
            "grade_level": int(new_profile["grade_level"]),
            "login_username": child_username,
            "is_active": bool(new_profile["is_active"]),
        },
        status_code=status.HTTP_201_CREATED,
    )


@app.get("/api/parent/child-accounts")
def list_child_accounts(
    username: str = Depends(_require_authenticated_parent),
) -> JSONResponse:
    with get_connection() as connection:
        parent = get_user_by_username(connection, username)
        rows = connection.execute(
            """
            SELECT cp.id, cp.display_name, cp.grade_level, cp.is_active,
                   cp.login_user_id, u.username AS login_username
            FROM child_profiles cp
            LEFT JOIN users u ON u.id = cp.login_user_id
            WHERE cp.user_id = ?
            ORDER BY cp.id
            """,
            (int(parent["id"]),),
        ).fetchall()

    return JSONResponse(
        {
            "children": [
                {
                    "id": int(row["id"]),
                    "display_name": row["display_name"],
                    "grade_level": int(row["grade_level"]),
                    "is_active": bool(row["is_active"]),
                    "login_username": row["login_username"],
                }
                for row in rows
            ]
        }
    )


@app.post("/api/parent/active-child/{child_profile_id}")
def set_active_child_profile(
    child_profile_id: int,
    request: Request,
    username: str = Depends(_require_authenticated_parent),
) -> JSONResponse:
    with get_connection() as connection:
        parent = get_user_by_username(connection, username)
        row = connection.execute(
            "SELECT id FROM child_profiles WHERE id = ? AND user_id = ? AND is_active = 1",
            (child_profile_id, int(parent["id"])),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found for this parent.",
        )
    request.session["active_child_profile_id"] = child_profile_id
    return JSONResponse({"active_child_profile_id": child_profile_id})


@app.post("/api/admin/content/reload")
def admin_reload_content(
    _: str = Depends(_require_authenticated_parent),
) -> JSONResponse:
    """Drop the cached seed activity list, verify the manifest, then reload.

    Lets a parent pick up content edits without restarting the container.
    Returns the recomputed counts so the caller knows how much the catalog
    just changed.
    """
    list_seed_activities.cache_clear()
    try:
        manifest = verify_content_manifest()
        activities = list_seed_activities()
        themes = list_seed_themes()
    except ValueError as exc:
        # Leave the cache cleared so the next call retries cleanly.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content reload failed: {exc}",
        ) from exc
    return JSONResponse(
        {
            "status": "ok",
            "content_version": manifest["content_version"],
            "activity_count": len(activities),
            "theme_count": len(themes),
        }
    )


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request) -> JSONResponse:
    rate_key = _client_ip(request)
    gate = login_limiter.check(rate_key)
    if not gate.allowed:
        return JSONResponse(
            {"error": "Too many login attempts. Please wait and try again."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(max(1, int(gate.retry_after_seconds)))},
        )

    invalid = JSONResponse(
        {"error": "Invalid credentials"},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )

    try:
        with get_connection() as connection:
            user_row = get_user_by_username(connection, payload.username)
    except ValueError:
        login_limiter.register_failure(rate_key)
        return invalid

    stored_hash = user_row["password_hash"] if "password_hash" in user_row.keys() else None
    if not stored_hash or not verify_password(payload.password, stored_hash):
        login_limiter.register_failure(rate_key)
        return invalid

    login_limiter.clear(rate_key)
    request.session["authenticated"] = True
    request.session["username"] = user_row["username"]
    request.session["role"] = user_row["role"]
    return JSONResponse(
        {
            "authenticated": True,
            "username": user_row["username"],
            "role": user_row["role"],
        }
    )


@app.post("/api/auth/logout")
def logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"authenticated": False})


@app.post("/api/auth/password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    username: str = Depends(_require_authenticated_username),
) -> JSONResponse:
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="New password must differ from current password.",
        )

    rate_key = _client_ip(request)
    gate = login_limiter.check(rate_key)
    if not gate.allowed:
        return JSONResponse(
            {"error": "Too many failed attempts. Please wait and try again."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(max(1, int(gate.retry_after_seconds)))},
        )

    with get_connection() as connection:
        user_row = get_user_by_username(connection, username)
        stored_hash = user_row["password_hash"] if "password_hash" in user_row.keys() else None
        if not stored_hash or not verify_password(payload.current_password, stored_hash):
            login_limiter.register_failure(rate_key)
            return JSONResponse(
                {"error": "Current password is incorrect."},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        new_hash = hash_password(payload.new_password)
        update_user_password(connection, username, new_hash)

    login_limiter.clear(rate_key)
    return JSONResponse({"status": "ok"})


@app.get("/api/dashboard")
def get_dashboard(
    request: Request,
    username: str = Depends(_require_authenticated_username),
) -> JSONResponse:
    activities = list_seed_activities()
    mission = activities[0]
    with get_connection() as connection:
        user = get_user_by_username(connection, username)
        child = _resolve_active_child_or_400(connection, request, user)
        rewards = get_reward_state(connection, int(user["id"]))
        progress = get_latest_progress_snapshot(connection, int(user["id"]), int(child["id"]))
        recent = get_recent_sessions(connection, int(child["id"]), limit=3)

    return JSONResponse(
        {
            "child_profile": {
                "display_name": child["display_name"],
                "grade_level": child["grade_level"],
            },
            "mission": {
                "activity_id": mission.id,
                "title": mission.title,
                "mission_label": mission.missionLabel,
                "skill_tags": mission.skillTags,
            },
            "rewards": {
                "stars": rewards["stars"],
                "streak_days": rewards["streak_days"],
                "badges": json.loads(rewards["badges_json"]),
            },
            "progress": {
                "completion_count": progress["completion_count"] if progress else 0,
                "average_score_percent": progress["average_score_percent"] if progress else 0,
                "strengths": json.loads(progress["strengths_json"]) if progress else [],
                "growth_areas": json.loads(progress["growth_areas_json"]) if progress else [],
            },
            "recent_sessions": [
                {
                    "session_id": row["session_uuid"],
                    "activity_id": row["activity_id"],
                    "activity_title": row["activity_title"],
                    "score_percent": row["score_percent"],
                    "submitted_at": row["submitted_at"],
                }
                for row in recent
            ],
        }
    )


@app.get("/api/activities")
def list_activities(
    _: str = Depends(_require_authenticated_username),
    theme: Optional[str] = Query(default=None),
    difficulty: Optional[str] = Query(default=None),
) -> JSONResponse:
    activities = list_seed_activities()
    allowed_themes = list_seed_themes()
    allowed_difficulties = list_seed_difficulty_tiers()
    if theme:
        if theme not in allowed_themes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f'Unsupported theme "{theme}".',
            )
        activities = [item for item in activities if item.theme == theme]
    if difficulty:
        if difficulty not in allowed_difficulties:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f'Unsupported difficulty "{difficulty}".',
            )
        activities = [item for item in activities if item.difficulty == difficulty]

    return JSONResponse(
        {
            "themes": allowed_themes,
            "difficulties": allowed_difficulties,
            "activities": [
                {
                    "id": item.id,
                    "title": item.title,
                    "theme": item.theme,
                    "difficulty": item.difficulty,
                    "passage_type": item.passageType,
                    "mission_label": item.missionLabel,
                    "skill_tags": item.skillTags,
                }
                for item in activities
            ]
        }
    )


@app.get("/api/activities/{activity_id}")
def get_activity(activity_id: str, _: str = Depends(_require_authenticated_username)) -> JSONResponse:
    try:
        activity = get_seed_activity(activity_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return JSONResponse(
        {
            "id": activity.id,
            "title": activity.title,
            "theme": activity.theme,
            "difficulty": activity.difficulty,
            "passage_type": activity.passageType,
            "mission_label": activity.missionLabel,
            "passage_title": activity.passageTitle,
            "passage_text": activity.passageText,
            "skill_tags": activity.skillTags,
            "questions": [
                {
                    "id": question.id,
                    "type": question.type,
                    "prompt": question.prompt,
                    "choices": question.choices,
                }
                for question in activity.questions
            ],
        }
    )


@app.post("/api/activities/{activity_id}/submit")
def submit_activity(
    activity_id: str,
    payload: SubmitActivityRequest,
    request: Request,
    username: str = Depends(_require_authenticated_username),
) -> JSONResponse:
    try:
        activity = get_seed_activity(activity_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    question_map = {question.id: question for question in activity.questions}
    submitted_lookup: Dict[str, Dict[str, Optional[str]]] = {}
    stored_responses: List[Dict[str, Optional[str]]] = []

    for answer in payload.responses:
        question = question_map.get(answer.question_id)
        if question is None:
            raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f'Unknown question_id "{answer.question_id}" for activity "{activity_id}".',
            )
        if question.type == "multiple-choice":
            if not answer.answer_choice:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f'Missing answer_choice for question "{answer.question_id}".',
                )
            submitted_lookup[answer.question_id] = {"answer_choice": answer.answer_choice, "answer_text": None}
            stored_responses.append(
                {
                    "question_id": answer.question_id,
                    "question_type": "multiple-choice",
                    "answer_choice": answer.answer_choice,
                    "answer_text": None,
                }
            )
        else:
            if not answer.answer_text:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f'Missing answer_text for question "{answer.question_id}".',
                )
            submitted_lookup[answer.question_id] = {"answer_choice": None, "answer_text": answer.answer_text}
            stored_responses.append(
                {
                    "question_id": answer.question_id,
                    "question_type": "short-response",
                    "answer_choice": None,
                    "answer_text": answer.answer_text,
                }
            )

    scoring = score_activity_submission(activity, submitted_lookup)

    with get_connection() as connection:
        user = get_user_by_username(connection, username)
        child = _resolve_active_child_or_400(connection, request, user)
        submission = create_submission(
            connection,
            int(user["id"]),
            int(child["id"]),
            activity.id,
            activity.title,
            stored_responses,
            scoring,
        )

    return JSONResponse(
        {
            "session_id": submission["session_uuid"],
            "activity_id": activity.id,
            "total_score": scoring["total_score"],
            "max_score": scoring["max_score"],
            "score_percent": scoring["score_percent"],
            "question_feedback": scoring["question_feedback"],
            "rubric": scoring["rubric"],
            "skill_breakdown": scoring["skill_breakdown"],
            "reward_snapshot": submission["reward_snapshot"],
        }
    )


@app.get("/api/progress/parent")
def get_parent_progress(
    request: Request,
    username: str = Depends(_require_authenticated_parent),
) -> JSONResponse:
    with get_connection() as connection:
        user = get_user_by_username(connection, username)
        child = _resolve_active_child_or_400(connection, request, user)
        projection = fetch_parent_progress_projection(connection, int(child["id"]))
        sessions = get_recent_sessions(connection, int(child["id"]), limit=10)
        latest_snapshot = get_latest_progress_snapshot(connection, int(user["id"]), int(child["id"]))
        score_history = get_recent_score_history(connection, int(child["id"]), limit=5)
        writing_feedback = get_recent_writing_feedback(connection, int(child["id"]), limit=3)
        skill_windows = compute_skill_windows(
            connection,
            int(child["id"]),
            tz=settings.learning_day_timezone,
        )
        recent_response_rows = get_recent_responses_with_activity(
            connection, int(child["id"]), limit=8
        )
        rewards = get_reward_state(connection, int(user["id"]))
    practice_next = recommend_practice_next(skill_windows)
    recent_questions = _hydrate_recent_questions(recent_response_rows)
    ai_usage = ai_quota.check(int(user["id"]))

    if len(score_history) < 2:
        trend = "starting"
    else:
        latest = score_history[0]
        previous = score_history[1]
        if latest > previous + 5:
            trend = "improving"
        elif latest < previous - 5:
            trend = "needs-support"
        else:
            trend = "steady"

    strengths = json.loads(latest_snapshot["strengths_json"]) if latest_snapshot else []
    growth_areas = json.loads(latest_snapshot["growth_areas_json"]) if latest_snapshot else []
    skill_summary = {
        "strength": strengths[0] if strengths else "building-foundation",
        "struggle": growth_areas[0] if growth_areas else "none-yet",
    }

    return JSONResponse(
        {
            "child_profile": {
                "display_name": projection["display_name"],
                "grade_level": projection["grade_level"],
            },
            "summary": {
                "session_count": projection["session_count"],
                "average_score_percent": round(float(projection["avg_score_percent"]), 2),
                "last_submitted_at": projection["last_submitted_at"],
                "strengths": strengths,
                "growth_areas": growth_areas,
                "trend": trend,
                "skill_summary": skill_summary,
            },
            "recent_sessions": [
                {
                    "session_id": row["session_uuid"],
                    "activity_id": row["activity_id"],
                    "activity_title": row["activity_title"],
                    "score_percent": row["score_percent"],
                    "submitted_at": row["submitted_at"],
                }
                for row in sessions
            ],
            "writing_feedback_summaries": writing_feedback,
            "skill_history": skill_windows,
            "practice_next": practice_next,
            "recent_questions": recent_questions,
            "rewards": {
                "stars": rewards["stars"],
                "streak_days": rewards["streak_days"],
                "badges": json.loads(rewards["badges_json"]),
            },
            "ai_usage": {
                "enabled": ai_quota.is_enabled,
                "used": ai_usage.used,
                "limit": ai_usage.limit,
                "remaining": max(0, ai_usage.limit - ai_usage.used) if ai_quota.is_enabled else None,
                "reset_at": ai_usage.reset_at.isoformat(),
            },
        }
    )


def _hydrate_recent_questions(rows: List[Dict]) -> List[Dict]:
    """Join recent-response DB rows with seeded activity metadata.

    Multiple-choice answers are surfaced because the choice is from a known
    list. Short-response answers intentionally do NOT include the verbatim
    text — that mirrors the existing writing_feedback_summaries shape and
    keeps child free text out of any logged/serialized place beyond the row
    itself.
    """
    output: List[Dict] = []
    for row in rows:
        try:
            activity = get_seed_activity(row["activity_id"])
        except ValueError:
            continue
        question = next((q for q in activity.questions if q.id == row["question_id"]), None)
        if question is None:
            continue
        entry: Dict = {
            "session_id": row["session_uuid"],
            "activity_id": row["activity_id"],
            "activity_title": row["activity_title"],
            "question_id": row["question_id"],
            "question_type": row["question_type"],
            "prompt": question.prompt,
            "skill_tags": activity.skillTags,
            "submitted_at": row["submitted_at"],
        }
        if row["question_type"] == "multiple-choice":
            entry["child_answer"] = row["answer_choice"] or ""
            entry["correct_answer"] = question.correctChoice or ""
            entry["is_correct"] = entry["child_answer"] == entry["correct_answer"]
        else:
            entry["child_answer"] = None
            entry["correct_answer"] = None
            entry["is_correct"] = None
        output.append(entry)
    return output


@app.get("/api/sessions/{session_id}")
def get_session_result(session_id: str, username: str = Depends(_require_authenticated_username)) -> JSONResponse:
    with get_connection() as connection:
        user = get_user_by_username(connection, username)
        session = fetch_session_result_by_uuid(connection, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Session "{session_id}" not found.')
    if int(session["user_id"]) != int(user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    metadata = json.loads(session["metadata_json"]) if session["metadata_json"] else {}
    reward_snapshot = metadata.get("reward_snapshot", {})

    return JSONResponse(
        {
            "session_id": session["session_uuid"],
            "activity_id": session["activity_id"],
            "activity_title": session["activity_title"],
            "submitted_at": session["submitted_at"],
            "total_score": session["total_score"],
            "max_score": session["max_score"],
            "score_percent": session["score_percent"],
            "rubric": json.loads(session["rubric_json"]),
            "skill_breakdown": json.loads(session["skill_breakdown_json"]),
            "reward_snapshot": reward_snapshot,
        }
    )


@app.get("/api/rewards")
def get_rewards(username: str = Depends(_require_authenticated_username)) -> JSONResponse:
    with get_connection() as connection:
        user = get_user_by_username(connection, username)
        rewards = get_reward_state(connection, int(user["id"]))
    return JSONResponse(
        {
            "stars": rewards["stars"],
            "streak_days": rewards["streak_days"],
            "badges": json.loads(rewards["badges_json"]),
        }
    )


@app.post("/api/ai/connectivity-check")
def ai_connectivity_check(
    payload: ConnectivityCheckRequest,
    username: str = Depends(_require_authenticated_parent),
) -> JSONResponse:
    with get_connection() as connection:
        user = get_user_by_username(connection, username)
    quota_response = _enforce_ai_quota(int(user["id"]))
    if quota_response is not None:
        return quota_response
    try:
        result = run_openrouter_connectivity_check(prompt=payload.prompt)
    except MissingOpenRouterKeyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except OpenRouterTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter timed out. Please try again.",
        ) from exc
    except OpenRouterProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter provider error. Please try again later.",
        ) from exc

    return JSONResponse(
        {
            "status": "ok",
            "model": result["model"],
            "prompt": result["prompt"],
            "response_text": result["response_text"],
        }
    )


@app.post("/api/ai/coach")
def ai_coach_feedback(
    payload: AICoachRequest,
    request: Request,
    username: str = Depends(_require_authenticated_username),
) -> JSONResponse:
    with get_connection() as connection:
        user = get_user_by_username(connection, username)
        child = _resolve_active_child_or_400(connection, request, user)
    quota_response = _enforce_ai_quota(int(user["id"]))
    if quota_response is not None:
        return quota_response
    with get_connection() as connection:
        session = fetch_session_result_by_uuid(connection, payload.session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Session "{payload.session_id}" not found.',
            )
        if int(session["user_id"]) != int(user["id"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        latest_snapshot = get_latest_progress_snapshot(connection, int(user["id"]), int(child["id"]))
        child_responses = get_session_responses(connection, int(session["id"]))

    activity = get_seed_activity(session["activity_id"])
    question_map = {q.id: q for q in activity.questions}
    questions_with_answers = []
    for resp in child_responses:
        q = question_map.get(resp["question_id"])
        entry: dict = {
            "question_id": resp["question_id"],
            "question_type": resp["question_type"],
            "prompt": q.prompt if q else "",
        }
        if resp["question_type"] == "multiple-choice":
            entry["child_answer"] = resp["answer_choice"] or ""
            entry["correct_answer"] = q.correctChoice if q else ""
            entry["is_correct"] = entry["child_answer"] == entry["correct_answer"]
        else:
            entry["child_answer"] = resp["answer_text"] or ""
        questions_with_answers.append(entry)

    context = {
        "activity_title": session["activity_title"],
        "passage_text": activity.passageText,
        "questions_with_answers": questions_with_answers,
        "score_percent": session["score_percent"],
        "rubric": json.loads(session["rubric_json"]),
        "skill_breakdown": json.loads(session["skill_breakdown_json"]),
        "strengths": json.loads(latest_snapshot["strengths_json"]) if latest_snapshot else [],
        "growth_areas": json.loads(latest_snapshot["growth_areas_json"]) if latest_snapshot else [],
    }

    try:
        coach_payload = generate_ai_coach_output(context, child_question=payload.child_question)
    except MissingOpenRouterKeyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except OpenRouterTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter timed out while generating coach feedback.",
        ) from exc
    except OpenRouterProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter provider error while generating coach feedback.",
        ) from exc

    with get_connection() as connection:
        if payload.child_question:
            insert_chat_message(
                connection,
                user_id=int(user["id"]),
                child_profile_id=int(child["id"]),
                session_id=int(session["id"]),
                role="user",
                content=payload.child_question,
                metadata={"source": "ai_coach", "scope": "post_submission"},
            )
        insert_chat_message(
            connection,
            user_id=int(user["id"]),
            child_profile_id=int(child["id"]),
            session_id=int(session["id"]),
            role="assistant",
            content=coach_payload["message_to_child"],
            metadata={
                "source": "ai_coach",
                "used_fallback": coach_payload["used_fallback"],
                "model": coach_payload["model"],
            },
        )

    return JSONResponse(coach_payload)


def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


def _is_protected_route(path: str) -> bool:
    clean_path = path.strip("/")
    if clean_path == "":
        return True
    first_segment = clean_path.split("/", maxsplit=1)[0]
    return first_segment in PROTECTED_ROUTE_PREFIXES


def _is_public_route(path: str) -> bool:
    clean_path = path.strip("/")
    if clean_path == "":
        return False
    first_segment = clean_path.split("/", maxsplit=1)[0]
    return first_segment in PUBLIC_ROUTE_PREFIXES


def _resolve_static_file(request_path: str) -> Path:
    clean_path = request_path.strip("/")
    static_root = STATIC_DIR.resolve()
    if not clean_path:
        return static_root / "index.html"

    direct_target = (STATIC_DIR / clean_path).resolve()
    if not str(direct_target).startswith(str(static_root)):
        return static_root / "index.html"

    if direct_target.is_file():
        return direct_target

    nested_index = (direct_target / "index.html").resolve()
    if str(nested_index).startswith(str(static_root)) and nested_index.is_file():
        return nested_index

    html_target = (STATIC_DIR / f"{clean_path}.html").resolve()
    if str(html_target).startswith(str(static_root)) and html_target.is_file():
        return html_target

    return static_root / "index.html"


@app.get("/{path:path}", include_in_schema=False)
def serve_static(path: str, request: Request):
    if not _is_authenticated(request) and _is_protected_route(path):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    if _is_authenticated(request) and path.strip("/") == "login":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    if not _is_public_route(path) and not _is_protected_route(path):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    target_file = _resolve_static_file(path)
    return FileResponse(target_file)
