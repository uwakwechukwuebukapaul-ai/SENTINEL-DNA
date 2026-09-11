#!/usr/bin/env sh
set -eu

base_url="${SENTINEL_DNA_BASE_URL:-}"
case "$base_url" in
  https://*) ;;
  *) echo "SENTINEL_DNA_BASE_URL must use HTTPS" >&2; exit 1 ;;
esac
ca_file="${SENTINEL_DNA_TLS_CA_FILE:-}"
if [ -z "$ca_file" ] || [ ! -f "$ca_file" ]; then
  echo "SENTINEL_DNA_TLS_CA_FILE must point to the trusted staging CA certificate" >&2
  exit 1
fi

# Keep verification enabled and make the trust anchor explicit. This avoids
# relying on a host-global trust-store mutation and never falls back to -k.
health="$(curl --fail --silent --show-error --cacert "$ca_file" "$base_url/health")"
ready="$(curl --fail --silent --show-error --cacert "$ca_file" "$base_url/ready")"
echo "health: $health"
echo "ready: $ready"
