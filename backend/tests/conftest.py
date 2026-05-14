"""Shared pytest setup for backend tests.

Every test runs against a fresh SQLite database at a tmp path so:
- the on-disk dev database is never read or mutated by the suite, and
- schema migrations + bootstrap seeding always run before a test calls into
  the API (some tests bypass FastAPI's lifespan via ASGITransport).
"""
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "ela-shared-test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    # Import lazily so tests that don't need the DB pay no extra import cost
    # at collection time.
    from backend.app.db import ensure_database

    ensure_database()
    return db_path


@pytest.fixture(autouse=True)
def reset_login_limiter() -> None:
    """Login limiter is module-level; clear it between tests so failed-login
    cases in one test don't poison the bucket for another."""
    from backend.app.main import login_limiter

    login_limiter.reset()
    yield
    login_limiter.reset()
