"""Tests for the versioned migration runner.

These create their own DBs (not the autouse one) so they can simulate
pre-existing schemas and inspect the migration history table directly.
"""
from pathlib import Path

import pytest

from backend.app.db import create_schema, ensure_database, get_connection
from backend.app.migrations import MIGRATIONS, applied_migration_ids, run_migrations


def _expected_migration_ids() -> set[int]:
    return {m.id for m in MIGRATIONS}


def test_run_migrations_on_fresh_schema_records_all_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.sqlite3"
    with get_connection(db_path) as connection:
        create_schema(connection)
        newly_applied = run_migrations(connection)

    assert sorted(newly_applied) == sorted(_expected_migration_ids())

    with get_connection(db_path) as connection:
        assert applied_migration_ids(connection) == _expected_migration_ids()


def test_run_migrations_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "idem.sqlite3"
    with get_connection(db_path) as connection:
        create_schema(connection)
        first = run_migrations(connection)
        second = run_migrations(connection)
        third = run_migrations(connection)

    assert sorted(first) == sorted(_expected_migration_ids())
    assert second == []
    assert third == []


def test_run_migrations_applies_missing_columns_on_legacy_schema(tmp_path: Path) -> None:
    """Simulate a DB created before iteration 2: users has only username + created_at."""
    db_path = tmp_path / "legacy.sqlite3"
    with get_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        connection.execute("INSERT INTO users (username) VALUES (?)", ("legacy",))
        connection.commit()

        run_migrations(connection)

        cols = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        assert "password_hash" in cols
        assert "role" in cols

        legacy_row = connection.execute(
            "SELECT username, password_hash, role FROM users WHERE username = ?",
            ("legacy",),
        ).fetchone()
        assert legacy_row["username"] == "legacy"
        assert legacy_row["password_hash"] is None
        assert legacy_row["role"] == "parent"


def test_ensure_database_smoke_from_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: a brand-new file becomes a usable DB with seed user + migrations recorded."""
    db_path = tmp_path / "smoke.sqlite3"
    assert not db_path.exists()

    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    ensure_database()

    assert db_path.exists()
    with get_connection(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"users", "child_profiles", "schema_migrations"}.issubset(tables)

        user = connection.execute(
            "SELECT username, password_hash, role FROM users WHERE username = ?",
            ("user",),
        ).fetchone()
        assert user is not None
        assert user["password_hash"] is not None
        assert user["role"] == "parent"

        assert applied_migration_ids(connection) == _expected_migration_ids()
