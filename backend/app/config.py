"""Application configuration loaded from environment variables.

Centralized so we have one place to validate required settings at startup
and one place to update defaults. Importing this module never raises;
``load_settings`` performs validation and is called by ``get_settings``.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal, Mapping, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

Environment = Literal["dev", "prod"]
SameSite = Literal["lax", "strict", "none"]

DEV_SESSION_SECRET = "ela-dev-session-secret"
DEFAULT_SESSION_COOKIE_NAME = "ela_session"
DEV_BOOTSTRAP_USERNAME = "user"
DEV_BOOTSTRAP_PASSWORD = "password"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    env: Environment
    session_secret: str
    session_cookie_name: str
    session_cookie_secure: bool
    session_cookie_samesite: SameSite
    bootstrap_username: str
    bootstrap_password: str
    login_rate_limit_max_attempts: int
    login_rate_limit_window_seconds: int
    csrf_allowed_origins: tuple[str, ...]
    learning_day_timezone: ZoneInfo

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _parse_bool(raw: Optional[str], *, default: bool) -> bool:
    if raw is None or raw == "":
        return default
    lowered = raw.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ConfigError(
        f"Invalid boolean value {raw!r}; expected one of true/false/1/0/yes/no/on/off."
    )


def _parse_env(raw: Optional[str]) -> Environment:
    if raw is None or raw == "":
        return "dev"
    lowered = raw.strip().lower()
    if lowered in ("dev", "development", "local"):
        return "dev"
    if lowered in ("prod", "production"):
        return "prod"
    raise ConfigError(f"Invalid ELA_ENV={raw!r}; expected dev or prod.")


def _parse_non_negative_int(raw: Optional[str], *, default: int, field_name: str) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{field_name} must be an integer; got {raw!r}.") from exc
    if value < 0:
        raise ConfigError(f"{field_name} must be >= 0; got {value}.")
    return value


def _parse_samesite(raw: Optional[str]) -> SameSite:
    if raw is None or raw == "":
        return "lax"
    lowered = raw.strip().lower()
    if lowered in ("lax", "strict", "none"):
        return lowered  # type: ignore[return-value]
    raise ConfigError(
        f"Invalid SESSION_COOKIE_SAMESITE={raw!r}; expected lax, strict, or none."
    )


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    """Read settings from ``env`` (defaults to ``os.environ``).

    In ``prod`` mode, ``SESSION_SECRET`` is required and must not equal the
    dev placeholder. In ``dev`` mode we fall back to the dev placeholder and
    log a warning so the default is visible in startup logs.
    """
    source = env if env is not None else os.environ
    app_env = _parse_env(source.get("ELA_ENV"))

    raw_secret = source.get("SESSION_SECRET", "").strip()
    if app_env == "prod":
        if not raw_secret:
            raise ConfigError(
                "SESSION_SECRET is required when ELA_ENV=prod. "
                "Generate a long random value and pass it via the environment."
            )
        if raw_secret == DEV_SESSION_SECRET:
            raise ConfigError(
                "SESSION_SECRET must not use the built-in dev placeholder in prod."
            )
        session_secret = raw_secret
    else:
        if raw_secret:
            session_secret = raw_secret
        else:
            logger.warning(
                "SESSION_SECRET not set; using insecure dev placeholder. "
                "Set SESSION_SECRET and ELA_ENV=prod before deploying."
            )
            session_secret = DEV_SESSION_SECRET

    cookie_name = source.get("SESSION_COOKIE_NAME", "").strip() or DEFAULT_SESSION_COOKIE_NAME
    cookie_secure_default = app_env == "prod"
    cookie_secure = _parse_bool(source.get("SESSION_COOKIE_SECURE"), default=cookie_secure_default)
    cookie_samesite = _parse_samesite(source.get("SESSION_COOKIE_SAMESITE"))

    if cookie_samesite == "none" and not cookie_secure:
        raise ConfigError(
            "SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE=true."
        )

    bootstrap_username = source.get("ELA_BOOTSTRAP_USERNAME", "").strip()
    bootstrap_password = source.get("ELA_BOOTSTRAP_PASSWORD", "")
    if app_env == "prod":
        if not bootstrap_username:
            raise ConfigError(
                "ELA_BOOTSTRAP_USERNAME is required when ELA_ENV=prod."
            )
        if not bootstrap_password:
            raise ConfigError(
                "ELA_BOOTSTRAP_PASSWORD is required when ELA_ENV=prod."
            )
        if bootstrap_password == DEV_BOOTSTRAP_PASSWORD:
            raise ConfigError(
                "ELA_BOOTSTRAP_PASSWORD must not use the built-in dev placeholder in prod."
            )
    else:
        if not bootstrap_username:
            bootstrap_username = DEV_BOOTSTRAP_USERNAME
        if not bootstrap_password:
            bootstrap_password = DEV_BOOTSTRAP_PASSWORD

    max_attempts = _parse_non_negative_int(
        source.get("LOGIN_RATE_LIMIT_MAX_ATTEMPTS"),
        default=10,
        field_name="LOGIN_RATE_LIMIT_MAX_ATTEMPTS",
    )
    window_seconds = _parse_non_negative_int(
        source.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS"),
        default=60,
        field_name="LOGIN_RATE_LIMIT_WINDOW_SECONDS",
    )

    csrf_allowed_origins = tuple(
        entry.strip()
        for entry in source.get("CSRF_ALLOWED_ORIGINS", "").split(",")
        if entry.strip()
    )

    tz_name = (source.get("LEARNING_DAY_TIMEZONE") or "UTC").strip()
    try:
        learning_day_timezone = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(
            f"LEARNING_DAY_TIMEZONE={tz_name!r} is not a recognized IANA timezone."
        ) from exc

    return Settings(
        env=app_env,
        session_secret=session_secret,
        session_cookie_name=cookie_name,
        session_cookie_secure=cookie_secure,
        session_cookie_samesite=cookie_samesite,
        bootstrap_username=bootstrap_username,
        bootstrap_password=bootstrap_password,
        login_rate_limit_max_attempts=max_attempts,
        login_rate_limit_window_seconds=window_seconds,
        csrf_allowed_origins=csrf_allowed_origins,
        learning_day_timezone=learning_day_timezone,
    )


_cached: Optional[Settings] = None


def get_settings() -> Settings:
    global _cached
    if _cached is None:
        _cached = load_settings()
    return _cached


def reset_settings_cache() -> None:
    """Drop the cached settings — used by tests that reload config."""
    global _cached
    _cached = None
