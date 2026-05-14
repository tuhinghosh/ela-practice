from pathlib import Path

import pytest

from backend.app.backup import BackupError, backup_database
from backend.app.db import ensure_database, get_connection


def _seed_marker_row(db_path: Path, marker: str) -> None:
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'parent')",
            (marker, "pbkdf2_sha256$1000$YWFh$YWFh"),
        )
        connection.commit()


def test_backup_creates_readable_copy_with_same_rows(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "snapshots" / "snap.sqlite3"
    ensure_database(source)
    _seed_marker_row(source, "marker-A")

    written = backup_database(target, source=source)

    assert written == target
    assert target.exists()
    with get_connection(target) as connection:
        rows = {
            row["username"]
            for row in connection.execute("SELECT username FROM users").fetchall()
        }
    assert "marker-A" in rows
    assert "user" in rows  # seeded bootstrap row was copied too


def test_backup_refuses_to_overwrite_by_default(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "snap.sqlite3"
    ensure_database(source)
    target.write_bytes(b"pre-existing")

    with pytest.raises(BackupError, match="already exists"):
        backup_database(target, source=source)


def test_backup_overwrites_when_requested(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "snap.sqlite3"
    ensure_database(source)
    target.write_bytes(b"pre-existing")

    backup_database(target, source=source, overwrite=True)

    # A real SQLite file starts with the magic header "SQLite format 3\x00".
    assert target.read_bytes().startswith(b"SQLite format 3")


def test_backup_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(BackupError, match="does not exist"):
        backup_database(tmp_path / "snap.sqlite3", source=tmp_path / "missing.sqlite3")


def test_backup_rejects_same_source_and_target(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    ensure_database(source)
    with pytest.raises(BackupError, match="must be different"):
        backup_database(source, source=source, overwrite=True)
