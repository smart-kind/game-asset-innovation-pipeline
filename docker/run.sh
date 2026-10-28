#!/usr/bin/env bash
set -e -o pipefail

run() {
  local scriptdir=$(dirname "${BASH_SOURCE[0]}")
  cd "$scriptdir" || exit 1

  # create .env file if it doesn't exist, otherwise docker compose will fail
  touch .env

  docker compose build
  printf "%s\n" "starting service invokeai"
  docker compose up -d invokeai
  docker compose logs -f invokeai
}

run
