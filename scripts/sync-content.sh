#!/usr/bin/env bash
# Sync canonical content from backend/content -> frontend/src/content.
# Run after editing files under backend/content/.
#
# Usage:
#   scripts/sync-content.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

python3 -m backend.app.content_cli validate
python3 -m backend.app.content_cli sync
