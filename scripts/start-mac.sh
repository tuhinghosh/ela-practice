#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="ela-mvp"
CONTAINER_NAME="ela-mvp"
DATA_DIR="$(pwd)/backend/data"

mkdir -p "$DATA_DIR"

if [ -n "$(docker ps -aq -f "name=^${CONTAINER_NAME}$")" ]; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

docker build -t "$IMAGE_NAME" .

if [ -f ".env" ]; then
  docker run -d --name "$CONTAINER_NAME" --env-file .env -p 8000:8000 -v "$DATA_DIR:/app/backend/data" "$IMAGE_NAME" >/dev/null
else
  docker run -d --name "$CONTAINER_NAME" -p 8000:8000 -v "$DATA_DIR:/app/backend/data" "$IMAGE_NAME" >/dev/null
fi

echo "ELA MVP started at http://localhost:8000"
