"""CLI: keep the N most recent SQLite backup files in a directory.

Symmetric with ``backend.app.ai_quota_prune``: a pure stdlib CLI safe to
run from cron, prints a one-line summary for log scraping.

Usage::

    python3 -m backend.app.backup_prune backups/ --keep 30
    python3 -m backend.app.backup_prune /var/backups/ela --keep 14 --pattern '*.sqlite3'
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from backend.app.backup import prune_backups


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m backend.app.backup_prune",
        description="Keep only the N most recent backup files in a directory.",
    )
    parser.add_argument("directory", type=Path, help="Directory containing backup files.")
    parser.add_argument(
        "--keep",
        type=int,
        required=True,
        help="Number of newest files to keep. Must be >= 0.",
    )
    parser.add_argument(
        "--pattern",
        default="*.sqlite3",
        help="Glob pattern selecting backup files (default: *.sqlite3).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.keep < 0:
        print(f"error: --keep must be >= 0; got {args.keep}", file=sys.stderr)
        return 2

    try:
        deleted = prune_backups(args.directory, keep=args.keep, pattern=args.pattern)
    except OSError as exc:
        print(f"error: failed to prune {args.directory}: {exc}", file=sys.stderr)
        return 2

    kept = max(0, len(list(args.directory.glob(args.pattern))) if args.directory.exists() else 0)
    print(
        f"backup_prune: removed {len(deleted)} file(s) from {args.directory} "
        f"(kept {kept}, pattern={args.pattern!r}, keep={args.keep})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
