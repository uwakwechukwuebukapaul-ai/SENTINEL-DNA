#!/usr/bin/env sh
set -eu

base_url="${SENTINEL_DNA_BASE_URL:-http://127.0.0.1:5000}"
case "$base_url" in
  https://*) ;;
  *) echo "SENTINEL_DNA_BASE_URL must use HTTPS" >&2; exit 1 ;;
esac
health="$(curl --fail --silent --show-error "$base_url/health")"
ready="$(curl --fail --silent --show-error "$base_url/ready")"
echo "health: $health"
echo "ready: $ready"
