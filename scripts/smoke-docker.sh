#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_ID="$$"
IMAGE_NAME="ela-smoke:${RUN_ID}"
FIRST_CONTAINER="ela-smoke-${RUN_ID}-first"
SECOND_CONTAINER="ela-smoke-${RUN_ID}-restart"
SMOKE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ela-smoke.XXXXXX")"
DATA_DIR="${SMOKE_DIR}/data"
STATE_FILE="${SMOKE_DIR}/state.json"
SMOKE_USERNAME="smoke-parent"
SMOKE_PASSWORD="smoke-password-${RUN_ID}"
SMOKE_SECRET="smoke-session-secret-${RUN_ID}-not-for-production"
HOST_PORT=""

mkdir -p "$DATA_DIR"

cleanup() {
  docker rm -f "$FIRST_CONTAINER" "$SECOND_CONTAINER" >/dev/null 2>&1 || true
  docker image rm "$IMAGE_NAME" >/dev/null 2>&1 || true
  rm -rf "$SMOKE_DIR"
}
trap cleanup EXIT INT TERM

cd "$REPO_ROOT"

HOST_PORT="$(
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
)"
BASE_URL="http://127.0.0.1:${HOST_PORT}"

start_container() {
  local container_name="$1"
  docker run -d \
    --name "$container_name" \
    -p "127.0.0.1:${HOST_PORT}:8000" \
    -v "${DATA_DIR}:/app/backend/data" \
    -e ELA_ENV=prod \
    -e SESSION_SECRET="$SMOKE_SECRET" \
    -e SESSION_COOKIE_SECURE=false \
    -e ELA_BOOTSTRAP_USERNAME="$SMOKE_USERNAME" \
    -e ELA_BOOTSTRAP_PASSWORD="$SMOKE_PASSWORD" \
    -e AI_CALLS_PER_USER_PER_DAY=0 \
    -e LEARNING_DAY_TIMEZONE=America/Los_Angeles \
    "$IMAGE_NAME" >/dev/null
}

wait_until_ready() {
  local container_name="$1"
  local attempt
  for attempt in $(seq 1 45); do
    if curl -fsS "${BASE_URL}/api/ready" >/dev/null 2>&1; then
      return 0
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null || true)" != "true" ]; then
      echo "Smoke container exited before becoming ready."
      docker logs "$container_name"
      return 1
    fi
    sleep 1
  done
  echo "Timed out waiting for ${BASE_URL}/api/ready."
  docker logs "$container_name"
  return 1
}

echo "1/7 Building production image..."
docker build -t "$IMAGE_NAME" .

echo "2/7 Starting isolated container..."
start_container "$FIRST_CONTAINER"

echo "3/7 Waiting for database and application readiness..."
wait_until_ready "$FIRST_CONTAINER"

echo "4/7 Exercising real login, content, submission, and results..."
python3 scripts/smoke_api.py \
  --phase initial \
  --base-url "$BASE_URL" \
  --username "$SMOKE_USERNAME" \
  --password "$SMOKE_PASSWORD" \
  --state-file "$STATE_FILE"

echo "5/7 Replacing the container while retaining its mounted data..."
docker rm -f "$FIRST_CONTAINER" >/dev/null
start_container "$SECOND_CONTAINER"

echo "6/7 Verifying readiness and persistence after replacement..."
wait_until_ready "$SECOND_CONTAINER"
python3 scripts/smoke_api.py \
  --phase restart \
  --base-url "$BASE_URL" \
  --username "$SMOKE_USERNAME" \
  --password "$SMOKE_PASSWORD" \
  --state-file "$STATE_FILE"

echo "7/7 Production Docker smoke harness passed."
