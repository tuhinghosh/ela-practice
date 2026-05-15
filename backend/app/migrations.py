"""Versioned, append-only SQLite migration runner.

Each migration is a function that takes a ``sqlite3.Connection`` and applies
exactly one schema or data change. Applied migrations are recorded in the
``schema_migrations`` table so reruns are no-ops. Migrations must:

- Be additive and idempotent (use ``IF NOT EXISTS`` / column-presence checks)
  so re-running on a partially-migrated DB is safe.
- Never be edited once shipped. To change something, add a new migration.

To add a new migration: write the function, give it the next sequential id,
and append it to ``MIGRATIONS``.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable, List, Set


@dataclass(frozen=True)
class Migration:
    id: int
    name: str
    apply: Callable[[sqlite3.Connection], None]


def _users_columns(connection: sqlite3.Connection) -> Set[str]:
    return {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}


def _migration_001_add_user_auth_columns(connection: sqlite3.Connection) -> None:
    """Add ``password_hash`` and ``role`` to ``users`` for hashed-credential login."""
    cols = _users_columns(connection)
    if "password_hash" not in cols:
        connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "role" not in cols:
        connection.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'parent'"
        )


def _migration_002_add_ai_call_log(connection: sqlite3.Connection) -> None:
    """Persist AI call counts so the per-user-per-day quota survives restarts.

    ``called_at`` is stored in UTC (``CURRENT_TIMESTAMP``). The index
    supports the count-by-(user, day) query the quota performs on every
    AI call.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS ai_call_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            called_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ai_call_log_user_day
            ON ai_call_log(user_id, called_at);
        """
    )


MIGRATIONS: List[Migration] = [
    Migration(
        id=1,
        name="add_user_auth_columns",
        apply=_migration_001_add_user_auth_columns,
    ),
    Migration(
        id=2,
        name="add_ai_call_log",
        apply=_migration_002_add_ai_call_log,
    ),
]


def _ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def applied_migration_ids(connection: sqlite3.Connection) -> Set[int]:
    _ensure_schema_migrations_table(connection)
    rows = connection.execute("SELECT id FROM schema_migrations").fetchall()
    return {int(row["id"]) for row in rows}


def run_migrations(connection: sqlite3.Connection) -> List[int]:
    """Apply any migrations whose ids are not yet recorded. Returns the list
    of ids newly applied (in order)."""
    _ensure_schema_migrations_table(connection)
    already_applied = applied_migration_ids(connection)
    newly_applied: List[int] = []
    for migration in sorted(MIGRATIONS, key=lambda m: m.id):
        if migration.id in already_applied:
            continue
        migration.apply(connection)
        connection.execute(
            "INSERT INTO schema_migrations (id, name) VALUES (?, ?)",
            (migration.id, migration.name),
        )
        newly_applied.append(migration.id)
    connection.commit()
    return newly_applied
