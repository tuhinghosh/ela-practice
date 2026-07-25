"""Content workflow CLI.

Subcommands:

- ``validate`` — re-runs every schema/cue check on ``backend/content`` and
  verifies the MANIFEST.json checksums. Exit code 0 on success, 1 on any
  validation failure.
- ``manifest`` — recomputes SHA256 checksums for the canonical files and
  writes MANIFEST.json. Use after editing content.
- ``audit`` — runs reviewed-library quality gates and prints a deterministic report.
- ``sync``   — copies the canonical JSON files from ``backend/content`` to
  ``frontend/src/content`` so the Next.js bundle stays aligned. Use after
  ``manifest``.

Run via ``python3 -m backend.app.content_cli <subcommand>``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from typing import Optional

from backend.app.content_schema import (
    ACTIVITIES_FILE,
    BACKEND_CONTENT_DIR,
    FRONTEND_CONTENT_DIR,
    MANIFEST_FILE,
    REVIEW_STATUS_FILE,
    SKILL_TAGS_FILE,
    THEMES_FILE,
    _hash_file,
    list_seed_activities,
    list_seed_themes,
    load_review_statuses,
    load_content_manifest,
    verify_content_manifest,
)

CANONICAL_FILES = (ACTIVITIES_FILE, SKILL_TAGS_FILE, THEMES_FILE, REVIEW_STATUS_FILE)


def cmd_validate(_args: argparse.Namespace) -> int:
    list_seed_activities.cache_clear()  # type: ignore[attr-defined]
    try:
        activities = list_seed_activities()
        themes = list_seed_themes()
        manifest = verify_content_manifest()
    except Exception as exc:
        print(f"content validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"ok: {len(activities)} activities, {len(themes)} themes, "
        f"manifest version={manifest['content_version']}"
    )
    return 0


def cmd_manifest(_args: argparse.Namespace) -> int:
    existing: dict = {}
    if MANIFEST_FILE.exists():
        existing = load_content_manifest()
    files = {path.name: _hash_file(path) for path in CANONICAL_FILES}
    manifest = {
        "content_version": existing.get("content_version", "1.0.0"),
        "files": files,
        "notes": existing.get(
            "notes",
            "Authoritative content lives here. Run scripts/sync-content.sh after "
            "editing to refresh the frontend mirror.",
        ),
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST_FILE}")
    return 0


def cmd_audit(_args: argparse.Namespace) -> int:
    from backend.app.content_audit import audit_content

    list_seed_activities.cache_clear()  # type: ignore[attr-defined]
    try:
        report = audit_content(list_seed_activities(), load_review_statuses())
    except Exception as exc:
        print(f"content audit failed: {exc}", file=sys.stderr)
        return 1
    print(f"review statuses: {report.status_counts}")
    print(f"reviewed difficulty tiers: {report.tier_counts}")
    print(f"correct-answer positions: {report.answer_position_counts}")
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    print(
        f"{'ok' if report.passed else 'failed'}: "
        f"{report.reviewed_count} reviewed activities, "
        f"{len(report.errors)} errors, {len(report.warnings)} warnings"
    )
    return 0 if report.passed else 1


def cmd_sync(_args: argparse.Namespace) -> int:
    FRONTEND_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    for path in CANONICAL_FILES:
        target = FRONTEND_CONTENT_DIR / path.name
        shutil.copyfile(path, target)
        print(f"synced {path.name} -> {target}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m backend.app.content_cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate canonical content + manifest").set_defaults(
        func=cmd_validate
    )
    subparsers.add_parser(
        "manifest", help="Recompute SHA256 checksums and rewrite MANIFEST.json"
    ).set_defaults(func=cmd_manifest)
    subparsers.add_parser(
        "audit", help="Run deterministic reviewed-content quality gates"
    ).set_defaults(func=cmd_audit)
    subparsers.add_parser(
        "sync", help="Copy backend/content files to frontend/src/content"
    ).set_defaults(func=cmd_sync)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
