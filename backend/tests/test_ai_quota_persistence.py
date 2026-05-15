"""Persistence-specific tests for the SQLite-backed AI call quota.

The pure rate-limit semantics live in test_observability.py against the
in-memory store. These tests focus on what changes when the store is
backed by SQLite:

- the ai_call_log table is created by migrations
- counts survive a fresh DailyAICallQuota instance against the same DB
  (i.e. a process restart)
- the day boundary is honored for date-stamped rows
- per-user isolation
- reset() truncates the table

Each test creates its own DB so the autouse conftest fixtures (which
also reset the module-level quota) do not interfere.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.ai_quota import (
    DailyAICallQuota,
    InMemoryQuotaStore,
    SQLiteQuotaStore,
)
from backend.app.db import ensure_database, get_connection


def _seed_user(db_path: Path, user_id: int, username: str) -> None:
    """Insert a user row so ai_call_log's FK is satisfied. Idempotent."""
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO users (id, username, password_hash, role) "
            "VALUES (?, ?, ?, 'parent')",
            (user_id, username, "pbkdf2_sha256$1000$YWFh$YWFh"),
        )
        connection.commit()


@pytest.fixture
def quota_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "quota.sqlite3"
    ensure_database(db_path)
    return db_path


@pytest.fixture
def sqlite_store(quota_db: Path) -> SQLiteQuotaStore:
    return SQLiteQuotaStore(lambda: get_connection(quota_db))


def test_migration_creates_ai_call_log_table(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.sqlite3"
    ensure_database(db_path)
    with get_connection(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "ai_call_log" in tables

        # Index supports the count-by-(user, day) lookup.
        indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_ai_call_log_user_day" in indexes


def test_sqlite_store_increment_then_count(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    # The bootstrap seed already created users(id=1, username='user').
    now = datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)
    assert sqlite_store.count_today(user_id=1, today=now.date()) == 0
    assert sqlite_store.increment(user_id=1, now=now) == 1
    assert sqlite_store.increment(user_id=1, now=now) == 2
    assert sqlite_store.count_today(user_id=1, today=now.date()) == 2


def test_quota_count_survives_a_fresh_instance(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    """Build a quota, register some calls, drop it on the floor, build a
    new quota against the same store. The replacement should see the
    prior counts."""
    _seed_user(quota_db, user_id=42, username="parent-42")
    clock_state = [datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)]
    first = DailyAICallQuota(
        daily_limit=5, store=sqlite_store, clock=lambda: clock_state[0]
    )
    first.register(user_id=42)
    first.register(user_id=42)
    first.register(user_id=42)

    # Simulate the process restarting — same store, fresh quota object.
    replacement = DailyAICallQuota(
        daily_limit=5, store=sqlite_store, clock=lambda: clock_state[0]
    )
    check = replacement.check(user_id=42)
    assert check.used == 3
    assert check.allowed is True
    assert check.limit == 5


def test_quota_blocks_after_persisted_calls_reach_limit(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    _seed_user(quota_db, user_id=7, username="parent-7")
    clock_state = [datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)]
    quota = DailyAICallQuota(
        daily_limit=3, store=sqlite_store, clock=lambda: clock_state[0]
    )
    for _ in range(3):
        assert quota.register(user_id=7).allowed is True
    # 4th call is over the cap.
    fourth = quota.register(user_id=7)
    assert fourth.allowed is False
    assert fourth.used == 4

    # And the same answer comes back via a fresh instance.
    replacement = DailyAICallQuota(
        daily_limit=3, store=sqlite_store, clock=lambda: clock_state[0]
    )
    assert replacement.check(user_id=7).allowed is False


def test_quota_day_rollover_ignores_yesterdays_rows(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    _seed_user(quota_db, user_id=11, username="parent-11")
    yesterday = datetime(2026, 5, 14, 23, 0, tzinfo=timezone.utc)
    today = datetime(2026, 5, 15, 0, 30, tzinfo=timezone.utc)
    # Pre-seed two calls "yesterday".
    sqlite_store.increment(user_id=11, now=yesterday)
    sqlite_store.increment(user_id=11, now=yesterday)

    clock_state = [today]
    quota = DailyAICallQuota(
        daily_limit=2, store=sqlite_store, clock=lambda: clock_state[0]
    )
    today_check = quota.check(user_id=11)
    assert today_check.used == 0
    assert today_check.allowed is True


def test_quota_isolates_users(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    _seed_user(quota_db, user_id=20, username="parent-20")
    _seed_user(quota_db, user_id=21, username="parent-21")
    clock_state = [datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)]
    quota = DailyAICallQuota(
        daily_limit=1, store=sqlite_store, clock=lambda: clock_state[0]
    )
    assert quota.register(user_id=20).allowed is True
    assert quota.register(user_id=21).allowed is True
    # Both users have now hit the limit independently.
    assert quota.register(user_id=20).allowed is False
    assert quota.register(user_id=21).allowed is False


def test_reset_truncates_persisted_log(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    clock_state = [datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)]
    quota = DailyAICallQuota(
        daily_limit=2, store=sqlite_store, clock=lambda: clock_state[0]
    )
    quota.register(user_id=1)
    quota.register(user_id=1)
    assert quota.check(user_id=1).used == 2

    quota.reset()

    assert quota.check(user_id=1).used == 0
    with get_connection(quota_db) as connection:
        count = connection.execute("SELECT COUNT(*) AS n FROM ai_call_log").fetchone()["n"]
    assert count == 0


def test_in_memory_store_still_works_for_unit_tests() -> None:
    """The in-memory store stays available for tests that do not want to
    pay for a SQLite round-trip per assertion."""
    clock_state = [datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)]
    quota = DailyAICallQuota(
        daily_limit=2,
        store=InMemoryQuotaStore(),
        clock=lambda: clock_state[0],
    )
    assert quota.register(user_id=1).allowed is True
    assert quota.register(user_id=1).allowed is True
    assert quota.register(user_id=1).allowed is False
