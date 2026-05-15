#!/usr/bin/env bash
# Keep only the N most recent SQLite backups in a directory.
#
# Usage:
#   scripts/prune-backups.sh [DIRECTORY] [--keep N]
#
# Defaults: DIRECTORY=backups, --keep=30. Symmetric with
# scripts/backup-db.sh; safe to run from cron.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,7p' "$0"
  exit 0
fi

DIRECTORY="backups"
KEEP="30"

while [ $# -gt 0 ]; do
  case "$1" in
    --keep)
      KEEP="$2"
      shift 2
      ;;
    *)
      DIRECTORY="$1"
      shift
      ;;
  esac
done

python3 -m backend.app.backup_prune "$DIRECTORY" --keep "$KEEP"
