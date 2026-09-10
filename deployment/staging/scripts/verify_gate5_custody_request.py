"""Fail-closed Gate 5 custody-request and external-authorization verifier.

This module prepares and verifies a request binding. It never creates an
authorization, signature, trust root, verifier identity, or release approval.
Cryptographic verification is an injected external boundary by design.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

COMMIT = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
LOCKED_BRANCH = "gate5-controlled-pilot-activation"
LOCKED_REPOSITORY = "uwakwechukwuebukpaul-ai/SENTINEL-DNA"
LOCKED_COMMIT = "4e35f0cb20cfab4779e1a567342e1855962ac58e"
LOCKED_IMAGE = "sentinel-dna:pilot-staging-candidate-4e35f0c"
LOCKED_DIGEST = "sha256:45ce0498839eb12fe07f08c9bb153bab5c9c7f2531b2b7a991f2ad1eec2e3995"
LOCKED_PACKAGE_ID = "gate5-custody-request-4e35f0c"
LOCKED_PROVENANCE = (
    "com.sentinel-dna.git.revision.full:4e35f0cb20cfab4779e1a567342e1855962ac58e",
    "org.opencontainers.image.revision:4e35f0cb20cfab4779e1a567342e1855962ac58e",
    "org.opencontainers.image.source:https://github.com/uwakwechukwuebukpaul-ai/SENTINEL-DNA",
)
CANONICAL_BASIS = (
    "schema_version", "governance_package_id", "candidate_commit", "candidate_branch",
    "repository", "image_reference", "image_digest", "provenance_reference",
    "approved_runtime_digest", "staging_origin", "activation_scope", "issued_at",
    "expires_at", "rollback_reference", "evidence_reference", "request_status",
)
# Verifier-side record of the original request. A changed request requires a
# new custody request and a separately reviewed recorded value.
LOCKED_REQUEST_HASH = "c34158ec997758a01693ee5561335d77b064dd04da38e0b7a15a9f3bcae9b1fc"
REQUIRED_REQUEST_FIELDS = {
    "schema_version", "artifact_type", "governance_package_id", "candidate_commit",
    "candidate_branch", "repository", "image_reference", "image_digest", "provenance_reference",
    "approved_runtime_digest", "staging_origin", "activation_scope", "issued_at",
    "expires_at", "rollback_reference", "evidence_reference", "verifier_identity",
    "operator_approval_reference", "signature_reference", "integrity", "request_status",
    "external_authority_requirements",
}
FORBIDDEN_LOCAL_MARKERS = ("repository", "local", "self", "test-only", "synthetic")


def _parse_time(value: Any, label: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not UTC.fullmatch(value):
        errors.append(f"{label}:utc_timestamp_required")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label}:invalid")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{label}:timezone_required")
        return None
    return parsed.astimezone(timezone.utc)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def request_hash(request: dict[str, Any]) -> str:
    body = {key: request[key] for key in CANONICAL_BASIS}
    return hashlib.sha256(_canonical(body)).hexdigest()


def verify_request(request: Any, *, expected_commit: str, expected_image_reference: str,
                   expected_image_digest: str, now: datetime | None = None) -> dict[str, Any]:
    errors: list[str] = []
    now = now or datetime.now(timezone.utc)
    if not isinstance(request, dict):
        return {"status": "BLOCKED", "errors": ["request:object_required"], "authorizes_release": False}
    unknown = set(request) - REQUIRED_REQUEST_FIELDS - {"staging_validation"}
    errors.extend(f"request.{key}:unknown" for key in sorted(unknown))
    errors.extend(f"request.{key}:missing" for key in sorted(REQUIRED_REQUEST_FIELDS - set(request)))
    if request.get("schema_version") != "1.0": errors.append("schema_version:unsupported")
    if request.get("artifact_type") != "GATE5_CUSTODY_REQUEST": errors.append("artifact_type:request_required")
    if request.get("request_status") != "PENDING_EXTERNAL_AUTHORIZATION": errors.append("request_status:must_remain_pending")
    if expected_commit != LOCKED_COMMIT or not COMMIT.fullmatch(expected_commit or "") or request.get("candidate_commit") != LOCKED_COMMIT:
        errors.append("candidate_commit:mismatch")
    if expected_image_reference != LOCKED_IMAGE or request.get("image_reference") != LOCKED_IMAGE:
        errors.append("image_reference:mismatch")
    if expected_image_digest != LOCKED_DIGEST or not DIGEST.fullmatch(expected_image_digest or "") or request.get("image_digest") != LOCKED_DIGEST:
        errors.append("image_digest:mismatch")
    if request.get("approved_runtime_digest") not in (None, expected_image_digest):
        errors.append("approved_runtime_digest:mismatch")
    if request.get("candidate_branch") != LOCKED_BRANCH: errors.append("candidate_branch:mismatch")
    if request.get("repository") != LOCKED_REPOSITORY: errors.append("repository:mismatch")
    if request.get("governance_package_id") != LOCKED_PACKAGE_ID: errors.append("governance_package_id:mismatch")
    if tuple(request.get("provenance_reference", ())) != LOCKED_PROVENANCE:
        errors.append("provenance_reference:mismatch")
    if request.get("rollback_reference") != "REQUIRED_FROM_EXTERNAL_AUTHORITY":
        errors.append("rollback_reference:external_reference_required")
    for field in ("verifier_identity", "operator_approval_reference", "signature_reference"):
        if request.get(field) is not None:
            errors.append(f"request.{field}:must_remain_unset_pending_external_authority")
    issued = _parse_time(request.get("issued_at"), "issued_at", errors)
    expires = _parse_time(request.get("expires_at"), "expires_at", errors)
    if issued and expires and expires <= issued: errors.append("validity:invalid_interval")
    if expires and expires <= now: errors.append("request:expired")
    integrity = request.get("integrity")
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256":
        errors.append("integrity:sha256_required")
    else:
        if tuple(integrity.get("canonical_basis", ())) != CANONICAL_BASIS:
            errors.append("integrity:canonical_basis_mismatch")
        if integrity.get("request_hash") != request_hash(request):
            errors.append("integrity:request_hash_mismatch")
        if integrity.get("request_hash") != LOCKED_REQUEST_HASH:
            errors.append("integrity:original_record_mismatch")
    return {"status": "PASS" if not errors else "BLOCKED", "errors": sorted(set(errors)), "authorizes_release": False}


def verify_external_authorization(request: dict[str, Any], authorization: Any, *,
                                  external_verifier: Callable[[dict[str, Any]], bool] | None = None,
                                  now: datetime | None = None) -> dict[str, Any]:
    """Verify an external authorization without supplying the trust decision.

    The callback must be provided by an independently controlled system. A
    repository-local callback, self-attested boolean, or absent callback is not
    accepted as authority.
    """
    errors: list[str] = []
    now = now or datetime.now(timezone.utc)
    if not isinstance(authorization, dict):
        return {"status": "BLOCKED", "errors": ["external_authorization:missing"], "authorizes_release": False}
    required = ("authorization_type", "request_id", "candidate_commit", "repository", "image_reference", "image_digest", "issued_at", "expires_at", "rollback_reference", "evidence_reference", "verifier_identity", "operator_approval_reference", "signature_reference", "integrity", "external_verification")
    for field in required:
        if not str(authorization.get(field, "")).strip(): errors.append(f"authorization.{field}:missing")
    if authorization.get("authorization_type") != "GATE5_CUSTODY_AUTHORIZATION": errors.append("authorization_type:external_authorization_required")
    if authorization.get("candidate_commit") != request.get("candidate_commit"): errors.append("authorization.candidate_commit:mismatch")
    if authorization.get("repository") != request.get("repository"): errors.append("authorization.repository:mismatch")
    if authorization.get("image_reference") != request.get("image_reference"): errors.append("authorization.image_reference:mismatch")
    if authorization.get("image_digest") != request.get("image_digest"): errors.append("authorization.image_digest:mismatch")
    if authorization.get("request_id") != request.get("governance_package_id"): errors.append("authorization.request_id:mismatch")
    verifier = str(authorization.get("verifier_identity", "")).lower()
    if any(marker in verifier for marker in FORBIDDEN_LOCAL_MARKERS): errors.append("authorization.verifier_identity:external_identity_required")
    for field in ("operator_approval_reference", "signature_reference"):
        if not str(authorization.get(field, "")).strip(): errors.append(f"authorization.{field}:missing")
    issued = _parse_time(authorization.get("issued_at"), "authorization.issued_at", errors)
    expires = _parse_time(authorization.get("expires_at"), "authorization.expires_at", errors)
    if issued and expires and expires <= issued: errors.append("authorization.validity:invalid_interval")
    if expires and expires <= now: errors.append("authorization:expired")
    integrity = authorization.get("integrity")
    if not isinstance(integrity, dict) or not str(integrity.get("reference", "")).strip() or integrity.get("algorithm") != "sha256":
        errors.append("authorization.integrity:external_reference_required")
    external = authorization.get("external_verification")
    if not isinstance(external, dict) or external.get("status") != "VERIFIED": errors.append("external_verification:verified_external_record_required")
    else:
        for field in ("trust_root_reference", "evidence_reference", "evidence_digest", "verification_method"):
            if not str(external.get(field, "")).strip(): errors.append(f"external_verification.{field}:missing")
        if not DIGEST.fullmatch(str(external.get("evidence_digest", ""))): errors.append("external_verification.evidence_digest:invalid")
    if callable(external_verifier):
        errors.append("external_verifier:repository_local_callable_forbidden")
    if errors:
        return {"status": "BLOCKED", "errors": sorted(set(errors)), "authorizes_release": False}
    # A repository-local value, callback, or boolean can never establish
    # authority. Cryptographic verification remains an external boundary.
    return {"status": "BLOCKED", "errors": ["cryptographic_evidence_verifier:external_authority_required"], "authorizes_release": False}


def verify_package(request: dict[str, Any], authorization: dict[str, Any] | None, **kwargs: Any) -> dict[str, Any]:
    local = verify_request(request, **{key: kwargs[key] for key in ("expected_commit", "expected_image_reference", "expected_image_digest", "now") if key in kwargs})
    if local["status"] != "PASS": return local
    return verify_external_authorization(request, authorization, external_verifier=kwargs.get("external_verifier"), now=kwargs.get("now"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-image-reference", required=True)
    parser.add_argument("--expected-image-digest", required=True)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        result = {"status": "BLOCKED", "errors": ["request:unreadable_or_invalid_json"], "authorizes_release": False}
    else:
        result = verify_request(request, expected_commit=args.expected_commit, expected_image_reference=args.expected_image_reference, expected_image_digest=args.expected_image_digest)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
