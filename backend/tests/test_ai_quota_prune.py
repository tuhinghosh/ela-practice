"""Tests for the ai_call_log retention / pruning."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.ai_quota import (
    DailyAICallQuota,
    InMemoryQuotaStore,
    SQLiteQuotaStore,
)
from backend.app.ai_quota_prune import main as prune_cli_main
from backend.app.config import ConfigError, load_settings
from backend.app.db import ensure_database, get_connection


@pytest.fixture
def quota_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "prune.sqlite3"
    ensure_database(db_path)
    return db_path


@pytest.fixture
def sqlite_store(quota_db: Path) -> SQLiteQuotaStore:
    return SQLiteQuotaStore(lambda: get_connection(quota_db))


def test_sqlite_prune_drops_old_keeps_recent(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    today = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    old = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
    cutoff = today - timedelta(days=30)

    # 3 old rows + 2 recent rows for the bootstrap user.
    for _ in range(3):
        sqlite_store.increment(user_id=1, now=old)
    for _ in range(2):
        sqlite_store.increment(user_id=1, now=today)

    removed = sqlite_store.prune_older_than(cutoff)
    assert removed == 3

    with get_connection(quota_db) as connection:
        remaining = connection.execute(
            "SELECT COUNT(*) AS n FROM ai_call_log"
        ).fetchone()["n"]
    assert remaining == 2

    # Recent count for today is still correct.
    assert sqlite_store.count_today(user_id=1, today=today.date()) == 2


def test_sqlite_prune_zero_rows_when_table_clean(
    sqlite_store: SQLiteQuotaStore,
) -> None:
    cutoff = datetime(2026, 5, 15, tzinfo=timezone.utc) - timedelta(days=30)
    assert sqlite_store.prune_older_than(cutoff) == 0


def test_in_memory_prune_drops_old_keeps_recent() -> None:
    store = InMemoryQuotaStore()
    today = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    old = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
    for _ in range(4):
        store.increment(user_id=1, now=old)
    for _ in range(2):
        store.increment(user_id=2, now=today)

    removed = store.prune_older_than(today - timedelta(days=30))
    assert removed == 4
    # User 1's old day is gone; user 2's today survives.
    assert store.count_today(user_id=1, today=old.date()) == 0
    assert store.count_today(user_id=2, today=today.date()) == 2


def test_quota_check_unaffected_by_prune(
    sqlite_store: SQLiteQuotaStore, quota_db: Path
) -> None:
    """Today's count must not change after pruning rows from prior months."""
    today = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    old = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    clock_state = [today]
    quota = DailyAICallQuota(
        daily_limit=3, store=sqlite_store, clock=lambda: clock_state[0]
    )
    # Pre-seed old rows and today's rows.
    sqlite_store.increment(user_id=1, now=old)
    sqlite_store.increment(user_id=1, now=old)
    quota.register(user_id=1)
    quota.register(user_id=1)

    assert quota.check(user_id=1).used == 2
    sqlite_store.prune_older_than(today - timedelta(days=30))
    assert quota.check(user_id=1).used == 2


def test_config_default_retention_is_90_days() -> None:
    settings = load_settings(env={})
    assert settings.ai_call_log_retention_days == 90


def test_config_accepts_zero_to_disable() -> None:
    settings = load_settings(env={"AI_CALL_LOG_RETENTION_DAYS": "0"})
    assert settings.ai_call_log_retention_days == 0


def test_config_rejects_negative_retention() -> None:
    with pytest.raises(ConfigError, match="must be >= 0"):
        load_settings(env={"AI_CALL_LOG_RETENTION_DAYS": "-1"})


def test_config_rejects_non_integer_retention() -> None:
    with pytest.raises(ConfigError, match="must be an integer"):
        load_settings(env={"AI_CALL_LOG_RETENTION_DAYS": "lots"})


def test_prune_cli_disabled_when_retention_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = prune_cli_main(["--days", "0"])
    assert code == 0
    out = capsys.readouterr().out
    assert "disabled" in out.lower()


def test_prune_cli_reports_deletion_count(
    quota_db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(quota_db))
    today = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    old = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    with get_connection(quota_db) as connection:
        for _ in range(5):
            connection.execute(
                "INSERT INTO ai_call_log (user_id, called_at) VALUES (?, ?)",
                (1, old.strftime("%Y-%m-%d %H:%M:%S")),
            )
        for _ in range(2):
            connection.execute(
                "INSERT INTO ai_call_log (user_id, called_at) VALUES (?, ?)",
                (1, today.strftime("%Y-%m-%d %H:%M:%S")),
            )
        connection.commit()

    code = prune_cli_main(["--days", "30"])
    assert code == 0
    out = capsys.readouterr().out
    assert "removed 5 rows" in out

    with get_connection(quota_db) as connection:
        remaining = connection.execute(
            "SELECT COUNT(*) AS n FROM ai_call_log"
        ).fetchone()["n"]
    assert remaining == 2


def test_prune_cli_rejects_negative_days(capsys: pytest.CaptureFixture[str]) -> None:
    code = prune_cli_main(["--days", "-3"])
    assert code == 2
    err = capsys.readouterr().err
    assert ">= 0" in err
