#!/usr/bin/env bash
# One-click deploy: build the API-only InvokeAI image and start it.
# Usage: cd <repo>/docker && bash deploy.sh
# Requires: Docker Desktop with docker compose on the target machine.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$ROOT/docker"
IMAGE_NAME="invokeai-api-only"

echo "==> 1/5 verify compose dir and Dockerfile"
cd "$COMPOSE_DIR"
if [[ ! -f "$COMPOSE_DIR/Dockerfile" ]]; then
  echo "Dockerfile not found at $COMPOSE_DIR/Dockerfile. Run from the repo's docker/ dir."
  exit 1
fi
if [[ ! -f .env ]]; then
  cp .env.sample .env
  echo "    .env created from .env.sample"
fi

echo "==> 2/5 build image ($IMAGE_NAME)"
docker compose build
docker images "$IMAGE_NAME" | head -3

echo "==> 3/5 init data dir + node packs"
# invokeai-data/nodes ships with the repo (4 node packs); on first boot
# load_custom_nodes auto-writes the README + custom_nodes scaffold.
mkdir -p "$COMPOSE_DIR/invokeai-data"

echo "==> 4/5 ensure .env (keep existing)"
if [[ ! -f "$COMPOSE_DIR/.env" ]]; then
  cp "$COMPOSE_DIR/.env.sample" "$COMPOSE_DIR/.env"
  echo "    .env created; fill INVOKEAI_EXTERNAL_*_API_KEY then restart"
else
  echo "    .env present, skipped"
fi

echo "==> 5/5 start container"
docker compose up -d
docker compose ps

cat <<EOF

Deploy done.
  service:  http://localhost:9090
  swagger:  http://localhost:9090/docs
  logs:     cd docker && docker compose logs -f invokeai

Next:
  1. edit docker/.env to set INVOKEAI_EXTERNAL_*_API_KEY, then
     docker compose restart invokeai
  2. add a node pack: cd docker/invokeai-data/nodes && git clone <repo>,
     then docker compose restart invokeai
  3. stop: cd docker && docker compose down
EOF
