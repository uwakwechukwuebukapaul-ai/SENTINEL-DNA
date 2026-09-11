"""Fail-closed, redacted Gate4 custody intake validator.

This tool reads configuration presence and non-secret shape only. It never
prints secret values, reads secret contents, creates files, invokes Docker, or
changes live infrastructure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$", re.IGNORECASE)
IMMUTABLE_IMAGE = re.compile(r"^\S+@sha256:[0-9a-f]{64}$", re.IGNORECASE)
CERTIFIED_HOSTNAME = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.IGNORECASE)
PLACEHOLDER = re.compile(r"(__[^\n]*__|<[^\n>]+>|TODO|CHANGE_ME|MUST_.*)", re.IGNORECASE)
WINDOWS_DEV_PATH = re.compile(r"(?:^|[/\\])users[/\\][^/\\]+[/\\]", re.IGNORECASE)

SECRETS = (
    "SENTINEL_DNA_STAGING_APP_SECRET_FILE",
    "SENTINEL_DNA_STAGING_POSTGRES_PASSWORD_FILE",
    "SENTINEL_DNA_STAGING_SMTP_USERNAME_FILE",
    "SENTINEL_DNA_STAGING_SMTP_PASSWORD_FILE",
    "SENTINEL_DNA_STAGING_TRUSTED_BROWSER_SERVICE_KEY_FILE",
)
ENVIRONMENT = (
    "SENTINEL_DNA_CERTIFIED_ORIGIN",
    "SENTINEL_DNA_CERTIFIED_HOSTNAME",
    "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST",
    "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT",
    "SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_READY",
    "SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_PROXY",
    "SENTINEL_DNA_EGRESS_GATEWAY_BIND",
    "SENTINEL_DNA_EGRESS_GATEWAY_PORT",
    "SENTINEL_DNA_TRUSTED_BROWSER_GATEWAY_UPLINK_NETWORK",
    "SENTINEL_DNA_STAGING_EDGE_CONFIG_FILE",
    "SENTINEL_DNA_STAGING_TLS_DIR",
    "SENTINEL_DNA_EGRESS_POLICY_FILE",
)
ARTIFACT_REFERENCES = (
    "SENTINEL_DNA_STAGING_APP_IMAGE",
    "SENTINEL_DNA_STAGING_EDGE_IMAGE",
    "SENTINEL_DNA_IMAGE_TAG",
    "SENTINEL_DNA_TRUSTED_BROWSER_IMAGE",
    "SENTINEL_DNA_EGRESS_GATEWAY_IMAGE",
    "SENTINEL_DNA_POSTGRES_IMAGE",
    "SENTINEL_DNA_REDIS_IMAGE",
    "SENTINEL_DNA_EGRESS_POLICY_REFERENCE",
)
PROVENANCE = (
    "SENTINEL_DNA_IMAGE_REVISION_FULL",
    "SENTINEL_DNA_IMAGE_CREATED",
    "SENTINEL_DNA_IMAGE_DIGEST",
    "SENTINEL_DNA_APPROVED_RUNTIME_DIGEST",
    "SENTINEL_DNA_EGRESS_POLICY_DIGEST",
    "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST",
)
RUNTIME_PROVIDER = (
    "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
    "SENTINEL_DNA_BROWSER_EXECUTABLE",
    "SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256",
    "SENTINEL_DNA_BROWSER_AUTH_BRIDGE",
    "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT",
    "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT",
    "PLAYWRIGHT_BASE_IMAGE",
)


def _present(env: dict[str, str], name: str) -> bool:
    return bool(str(env.get(name, "")).strip())


def _path_reason(value: str, *, must_exist: bool = False) -> str | None:
    if PLACEHOLDER.search(value) or WINDOWS_DEV_PATH.search(value):
        return "placeholder_or_developer_path"
    path = Path(value)
    if not path.is_absolute():
        return "protected_path_must_be_absolute"
    if must_exist and not path.exists():
        return "protected_path_unavailable"
    return None


def validate(env: dict[str, str] | None = None, *, check_paths: bool = False) -> dict[str, object]:
    values = dict(os.environ if env is None else env)
    missing: list[str] = []
    invalid: list[dict[str, str]] = []

    groups = {
        "REQUIRED_SECRET": SECRETS,
        "REQUIRED_ENVIRONMENT_CONFIGURATION": ENVIRONMENT,
        "REQUIRED_ARTIFACT_REFERENCE": ARTIFACT_REFERENCES,
        "REQUIRED_PROVENANCE_VALUE": PROVENANCE,
        "REQUIRED_RUNTIME_PROVIDER_INPUT": RUNTIME_PROVIDER,
    }
    for category, names in groups.items():
        for name in names:
            if not _present(values, name):
                missing.append(name)
            elif PLACEHOLDER.search(values[name]):
                invalid.append({"name": name, "category": category, "reason": "placeholder_value"})

    for name in ("SENTINEL_DNA_IMAGE_DIGEST", "SENTINEL_DNA_APPROVED_RUNTIME_DIGEST", "SENTINEL_DNA_EGRESS_POLICY_DIGEST", "SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256"):
        if _present(values, name) and not SHA256.fullmatch(values[name].strip()):
            invalid.append({"name": name, "category": "DIGEST", "reason": "sha256_required"})

    for name in (
        "SENTINEL_DNA_STAGING_APP_IMAGE",
        "SENTINEL_DNA_STAGING_EDGE_IMAGE",
        "SENTINEL_DNA_TRUSTED_BROWSER_IMAGE",
        "SENTINEL_DNA_EGRESS_GATEWAY_IMAGE",
        "SENTINEL_DNA_POSTGRES_IMAGE",
        "SENTINEL_DNA_REDIS_IMAGE",
    ):
        if _present(values, name) and not IMMUTABLE_IMAGE.fullmatch(values[name].strip()):
            invalid.append({"name": name, "category": "IMAGE_REFERENCE", "reason": "immutable_sha256_reference_required"})

    for name in (
        "SENTINEL_DNA_STAGING_APP_SECRET_FILE",
        "SENTINEL_DNA_STAGING_POSTGRES_PASSWORD_FILE",
        "SENTINEL_DNA_STAGING_SMTP_USERNAME_FILE",
        "SENTINEL_DNA_STAGING_SMTP_PASSWORD_FILE",
        "SENTINEL_DNA_STAGING_TRUSTED_BROWSER_SERVICE_KEY_FILE",
        "SENTINEL_DNA_STAGING_EDGE_CONFIG_FILE",
        "SENTINEL_DNA_STAGING_TLS_DIR",
        "SENTINEL_DNA_EGRESS_POLICY_FILE",
        "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST",
        "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
        "SENTINEL_DNA_BROWSER_EXECUTABLE",
        "SENTINEL_DNA_BROWSER_AUTH_BRIDGE",
    ):
        if _present(values, name):
            reason = _path_reason(values[name], must_exist=check_paths)
            if reason:
                invalid.append({"name": name, "category": "PROTECTED_PATH", "reason": reason})

    if _present(values, "SENTINEL_DNA_CERTIFIED_ORIGIN"):
        origin = values["SENTINEL_DNA_CERTIFIED_ORIGIN"].strip()
        if not origin.startswith("https://") or PLACEHOLDER.search(origin):
            invalid.append({"name": "SENTINEL_DNA_CERTIFIED_ORIGIN", "category": "ORIGIN", "reason": "approved_https_origin_required"})

    if _present(values, "SENTINEL_DNA_CERTIFIED_HOSTNAME"):
        hostname = values["SENTINEL_DNA_CERTIFIED_HOSTNAME"].strip().rstrip(".")
        if PLACEHOLDER.search(hostname) or not CERTIFIED_HOSTNAME.fullmatch(hostname):
            invalid.append({"name": "SENTINEL_DNA_CERTIFIED_HOSTNAME", "category": "ORIGIN", "reason": "certified_dns_hostname_required"})

    if _present(values, "SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_READY") and values["SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_READY"].strip().lower() != "true":
        invalid.append({"name": "SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_READY", "category": "READINESS", "reason": "must_be_true"})

    return {
        "schema": "sentinel-dna.gate4.custody-intake-result.v1",
        "status": "PASS" if not missing and not invalid else "BLOCKED",
        "missing": sorted(missing),
        "invalid": sorted(invalid, key=lambda item: (item["name"], item["reason"])),
        "secret_values_logged": False,
        "secret_contents_read": False,
        "live_operations_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-paths", action="store_true", help="check protected paths without reading secret contents")
    parser.add_argument("--json", action="store_true", help="emit the redacted result as JSON")
    args = parser.parse_args()
    result = validate(check_paths=args.check_paths)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"GATE4_CUSTODY_INTAKE={result['status']}")
        print(f"MISSING_COUNT={len(result['missing'])}")
        print(f"INVALID_COUNT={len(result['invalid'])}")
        for name in result["missing"]:
            print(f"MISSING={name}")
        for item in result["invalid"]:
            print(f"INVALID={item['name']}:{item['reason']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
