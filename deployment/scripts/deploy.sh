#!/usr/bin/env sh
set -eu

: "${STAGING_ENV_FILE:?STAGING_ENV_FILE must point to external staging configuration}"
: "${SENTINEL_DNA_BASE_URL:?SENTINEL_DNA_BASE_URL must point to the private staging edge}"
: "${SENTINEL_DNA_STAGING_TLS_DIR:?SENTINEL_DNA_STAGING_TLS_DIR must point to external staging TLS material}"
: "${SENTINEL_DNA_IMAGE_TAG:?SENTINEL_DNA_IMAGE_TAG must be derived from the reviewed checkout}"
: "${SENTINEL_DNA_IMAGE_REVISION_FULL:?SENTINEL_DNA_IMAGE_REVISION_FULL must be the full reviewed commit}"
: "${SENTINEL_DNA_IMAGE_CREATED:?SENTINEL_DNA_IMAGE_CREATED must be derived release metadata}"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
STAGING_COMPOSE="$REPOSITORY_ROOT/deployment/staging/docker-compose.yml"
STAGING_OVERRIDE="$REPOSITORY_ROOT/deployment/staging/docker-compose.pilot.override.yml"

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
if [ ! -f "$STAGING_OVERRIDE" ]; then
  echo "Pilot staging Compose override was not found" >&2
  exit 1
fi
if [ "$SENTINEL_DNA_BASE_URL" != "https://sentinel-dna-staging:18443" ]; then
  echo "SENTINEL_DNA_BASE_URL must use HTTPS and be the certified staging origin" >&2
  exit 1
fi

actual_revision=$(git -C "$REPOSITORY_ROOT" rev-parse HEAD 2>/dev/null || true)
if [ "$actual_revision" != "$SENTINEL_DNA_IMAGE_REVISION_FULL" ]; then
  echo "Staging checkout does not match the requested release revision" >&2
  exit 1
fi
if [ -n "$(git -C "$REPOSITORY_ROOT" status --porcelain --untracked-files=all)" ]; then
  echo "Staging checkout must be clean before an image build" >&2
  exit 1
fi

docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file "$STAGING_COMPOSE" \
  --file "$STAGING_OVERRIDE" \
  up -d --build postgres redis

docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file "$STAGING_COMPOSE" \
  --file "$STAGING_OVERRIDE" \
  run --rm --build migration

docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file "$STAGING_COMPOSE" \
  --file "$STAGING_OVERRIDE" \
  up -d --build app edge

staging_ca_file="${SENTINEL_DNA_STAGING_TLS_CA_FILE:-$SENTINEL_DNA_STAGING_TLS_DIR/staging-ca.crt}"
SENTINEL_DNA_TLS_CA_FILE="$staging_ca_file" \
  SENTINEL_DNA_BASE_URL="$SENTINEL_DNA_BASE_URL" \
"$SCRIPT_DIR/health_check.sh"
