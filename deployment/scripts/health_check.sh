#!/usr/bin/env sh
set -eu

base_url="${SENTINEL_DNA_BASE_URL:-http://127.0.0.1:5000}"
health="$(curl --fail --silent --show-error "$base_url/health")"
ready="$(curl --fail --silent --show-error "$base_url/ready")"
echo "health: $health"
echo "ready: $ready"
