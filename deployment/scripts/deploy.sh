#!/usr/bin/env sh
set -eu

: "${SENTINEL_DNA_ENV:=staging}"
if [ "$SENTINEL_DNA_ENV" != "staging" ]; then
  echo "SENTINEL_DNA_ENV must be staging" >&2
  exit 1
fi
if [ ! -f .env ]; then
  echo "Missing .env; copy .env.example and configure staging secrets" >&2
  exit 1
fi

docker compose up -d --build
"$(dirname "$0")/health_check.sh"
