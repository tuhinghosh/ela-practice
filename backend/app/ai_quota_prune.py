"""CLI: prune ``ai_call_log`` rows older than the configured retention.

Designed to run from cron. Reads ``AI_CALL_LOG_RETENTION_DAYS`` from the
environment (default 90; ``0`` disables and the script exits 0 without
touching the table). Prints the deletion count on a single line for easy
log scraping.

Usage::

    python3 -m backend.app.ai_quota_prune
    python3 -m backend.app.ai_quota_prune --days 30
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.app.ai_quota import SQLiteQuotaStore
from backend.app.config import get_settings
from backend.app.db import get_connection


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m backend.app.ai_quota_prune",
        description="Delete ai_call_log rows older than the retention window.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Retention window in days (overrides AI_CALL_LOG_RETENTION_DAYS).",
    )
    return parser


def main(
    argv: Optional[list[str]] = None,
    *,
    now: Optional[datetime] = None,
) -> int:
    args = _build_parser().parse_args(argv)
    settings = get_settings()
    days = args.days if args.days is not None else settings.ai_call_log_retention_days

    if days < 0:
        print(f"error: --days must be >= 0; got {days}", file=sys.stderr)
        return 2
    if days == 0:
        print("ai_quota_prune: retention=0 (disabled), nothing pruned")
        return 0

    reference_time = now or datetime.now(timezone.utc)
    if reference_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    cutoff = reference_time.astimezone(timezone.utc) - timedelta(days=days)
    store = SQLiteQuotaStore(get_connection)
    removed = store.prune_older_than(cutoff)
    print(
        f"ai_quota_prune: removed {removed} rows older than "
        f"{cutoff.isoformat()} (retention={days} days)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
