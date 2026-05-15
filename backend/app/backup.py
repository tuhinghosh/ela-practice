"""SQLite online backup helper.

Uses ``sqlite3.Connection.backup`` which copies a live database safely under
concurrent writes — preferred over plain file copy. Invokable as a module:

    python3 -m backend.app.backup /path/to/backup.sqlite3
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

from backend.app.db import get_database_path


class BackupError(RuntimeError):
    pass


def backup_database(
    target: Path,
    *,
    source: Optional[Path] = None,
    overwrite: bool = False,
) -> Path:
    """Write a hot backup of ``source`` (default: configured DB) to ``target``.

    Creates the parent directory if needed. Refuses to overwrite an existing
    file unless ``overwrite=True``.
    """
    src = Path(source) if source is not None else get_database_path()
    dst = Path(target)

    if not src.exists():
        raise BackupError(f"Source database does not exist: {src}")
    if dst.exists() and not overwrite:
        raise BackupError(
            f"Backup target already exists: {dst}. Pass --overwrite to replace it."
        )
    if dst.resolve() == src.resolve():
        raise BackupError("Backup target must be different from source path.")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and overwrite:
        dst.unlink()

    src_conn = sqlite3.connect(src)
    try:
        dst_conn = sqlite3.connect(dst)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    return dst


def prune_backups(
    directory: Path,
    *,
    keep: int,
    pattern: str = "*.sqlite3",
) -> List[Path]:
    """Delete the oldest backup files in ``directory`` until at most ``keep``
    remain, matched by ``pattern`` and ranked by mtime (newest first).

    Returns the list of deleted paths in the order they were deleted. A
    missing directory is treated as empty (no error). ``keep`` must be ``>= 0``.
    """
    if keep < 0:
        raise ValueError("keep must be >= 0.")
    if not directory.exists():
        return []
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    to_delete = candidates[keep:]
    deleted: List[Path] = []
    for path in to_delete:
        path.unlink()
        deleted.append(path)
    return deleted


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m backend.app.backup",
        description="Create a safe hot backup of the ELA SQLite database.",
    )
    parser.add_argument("target", type=Path, help="Path to write the backup file to.")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Override source DB path (defaults to DATABASE_PATH or backend/data/ela.sqlite3).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the target file if it already exists.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        written = backup_database(args.target, source=args.source, overwrite=args.overwrite)
    except BackupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Backup written: {written}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
