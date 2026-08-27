#!/usr/bin/env sh
set -eu

: "${STAGING_ENV_FILE:?STAGING_ENV_FILE must point to external staging configuration}"
: "${SENTINEL_DNA_BASE_URL:?SENTINEL_DNA_BASE_URL must point to the private staging edge}"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
STAGING_COMPOSE="$REPOSITORY_ROOT/deployment/staging/docker-compose.yml"

case "$STAGING_ENV_FILE" in
  /*) ;;
  *) echo "STAGING_ENV_FILE must be an absolute path outside the repository" >&2; exit 1 ;;
esac
case "$STAGING_ENV_FILE" in
  "$REPOSITORY_ROOT"/*) echo "STAGING_ENV_FILE must not be inside the repository" >&2; exit 1 ;;
esac
if [ ! -f "$STAGING_ENV_FILE" ]; then
  echo "External staging configuration was not found" >&2
  exit 1
fi
if [ ! -f "$STAGING_COMPOSE" ]; then
  echo "Staging Compose contract was not found" >&2
  exit 1
fi

docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file "$STAGING_COMPOSE" \
  up -d --build

"$SCRIPT_DIR/health_check.sh"
