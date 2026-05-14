#!/usr/bin/env bash
# Create a hot backup of the ELA SQLite database.
#
# Usage:
#   scripts/backup-db.sh [TARGET]
#
# TARGET defaults to backups/ela-<UTC timestamp>.sqlite3 under the repo root.
# The source DB is read from DATABASE_PATH or falls back to
# backend/data/ela.sqlite3 (matching the running app's default).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,11p' "$0"
  exit 0
fi

TARGET="${1:-backups/ela-$(date -u +%Y%m%dT%H%M%SZ).sqlite3}"
mkdir -p "$(dirname "$TARGET")"

python3 -m backend.app.backup "$TARGET"
