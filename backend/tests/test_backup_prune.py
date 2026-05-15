"""Tests for backup retention/pruning."""
import os
import time
from pathlib import Path
from typing import List

import pytest

from backend.app.backup import prune_backups
from backend.app.backup_prune import main as prune_cli_main


def _touch(path: Path, mtime: float) -> None:
    path.write_bytes(b"SQLite format 3\x00")  # plausible header for realism
    os.utime(path, (mtime, mtime))


def _make_backups(directory: Path, names: List[str]) -> List[Path]:
    """Create ``names`` in ``directory`` with mtime increasing in order
    (first name oldest, last name newest)."""
    directory.mkdir(parents=True, exist_ok=True)
    base = time.time() - 10_000
    paths: List[Path] = []
    for index, name in enumerate(names):
        path = directory / name
        _touch(path, base + index * 60)
        paths.append(path)
    return paths


def test_prune_keeps_newest_n_and_deletes_rest(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    paths = _make_backups(
        backup_dir,
        ["old1.sqlite3", "old2.sqlite3", "mid.sqlite3", "new1.sqlite3", "new2.sqlite3"],
    )

    deleted = prune_backups(backup_dir, keep=2)

    deleted_names = {p.name for p in deleted}
    surviving = {p.name for p in backup_dir.glob("*.sqlite3")}
    assert deleted_names == {"old1.sqlite3", "old2.sqlite3", "mid.sqlite3"}
    assert surviving == {"new1.sqlite3", "new2.sqlite3"}
    # All deleted paths actually gone.
    for path in paths[:3]:
        assert not path.exists()


def test_prune_keep_zero_deletes_everything(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    _make_backups(backup_dir, ["a.sqlite3", "b.sqlite3", "c.sqlite3"])
    deleted = prune_backups(backup_dir, keep=0)
    assert len(deleted) == 3
    assert list(backup_dir.glob("*.sqlite3")) == []


def test_prune_keep_larger_than_count_is_noop(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    _make_backups(backup_dir, ["a.sqlite3", "b.sqlite3"])
    deleted = prune_backups(backup_dir, keep=10)
    assert deleted == []
    assert len(list(backup_dir.glob("*.sqlite3"))) == 2


def test_prune_missing_directory_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "does-not-exist"
    deleted = prune_backups(target, keep=5)
    assert deleted == []


def test_prune_ignores_non_matching_files(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    _make_backups(backup_dir, ["old.sqlite3", "new.sqlite3"])
    (backup_dir / "README.md").write_text("not a backup", encoding="utf-8")
    (backup_dir / "log.txt").write_text("logs", encoding="utf-8")

    deleted = prune_backups(backup_dir, keep=1)
    assert {p.name for p in deleted} == {"old.sqlite3"}
    assert (backup_dir / "README.md").exists()
    assert (backup_dir / "log.txt").exists()


def test_prune_rejects_negative_keep(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="keep must be >= 0"):
        prune_backups(tmp_path, keep=-1)


def test_prune_respects_custom_pattern(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    _make_backups(backup_dir, ["a.db", "b.db", "c.db"])
    # Also drop in an unrelated .sqlite3 file that should not be touched.
    (backup_dir / "other.sqlite3").write_text("ignore me", encoding="utf-8")

    deleted = prune_backups(backup_dir, keep=1, pattern="*.db")
    assert {p.name for p in deleted} == {"a.db", "b.db"}
    assert (backup_dir / "other.sqlite3").exists()


def test_cli_reports_deletion_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    backup_dir = tmp_path / "backups"
    _make_backups(
        backup_dir,
        ["oldest.sqlite3", "older.sqlite3", "newest.sqlite3"],
    )

    code = prune_cli_main([str(backup_dir), "--keep", "1"])
    assert code == 0
    out = capsys.readouterr().out
    assert "removed 2 file(s)" in out
    assert "kept 1" in out


def test_cli_rejects_negative_keep(capsys: pytest.CaptureFixture[str]) -> None:
    code = prune_cli_main(["/tmp", "--keep", "-3"])
    assert code == 2
    err = capsys.readouterr().err
    assert ">= 0" in err


def test_cli_missing_directory_succeeds_with_zero_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = prune_cli_main([str(tmp_path / "absent"), "--keep", "5"])
    assert code == 0
    out = capsys.readouterr().out
    assert "removed 0 file(s)" in out
    assert "kept 0" in out
