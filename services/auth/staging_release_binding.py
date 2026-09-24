"""External, fail-closed release binding for the staging authority ceremony.

The final image digest is deliberately not a source constant.  A release
operator creates this document only after the immutable image exists, and
mounts it read-only together with a separately protected custody record.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping


SCHEMA_VERSION = "sentinel-dna-staging-release-binding-v1"
REPOSITORY = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA.git"
ENVIRONMENT = "staging"
DATABASE_TARGET = "postgresql://sentinel@postgres:5432/sentinel_dna"
MANIFEST_FIELDS = frozenset({
    "schema_version", "release_id", "environment", "repository",
    "commit", "tree", "image_repository", "image_digest",
    "database_target_identity", "created_at", "expires_at", "manifest_hash",
})
TRUST_FIELDS = frozenset({
    "schema_version", "manifest_hash", "commit", "tree", "image_digest",
})
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class StagingReleaseBindingError(ValueError):
    pass


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise StagingReleaseBindingError(f"{field}_invalid")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise StagingReleaseBindingError(f"{field}_invalid") from exc


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise StagingReleaseBindingError(f"{label}_path_invalid")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StagingReleaseBindingError(f"{label}_invalid") from exc
    if not isinstance(value, dict):
        raise StagingReleaseBindingError(f"{label}_invalid")
    return value


def validate_release_binding(manifest: Mapping[str, Any], *, now: datetime | None = None, require_active: bool = True) -> dict[str, Any]:
    if not isinstance(manifest, Mapping) or set(manifest) != MANIFEST_FIELDS:
        raise StagingReleaseBindingError("manifest_fields_invalid")
    normalized = dict(manifest)
    if normalized["schema_version"] != SCHEMA_VERSION:
        raise StagingReleaseBindingError("manifest_schema_invalid")
    if normalized["environment"] != ENVIRONMENT or normalized["repository"] not in {
        REPOSITORY, REPOSITORY.removesuffix(".git")
    }:
        raise StagingReleaseBindingError("manifest_scope_invalid")
    if normalized["database_target_identity"] != DATABASE_TARGET:
        raise StagingReleaseBindingError("manifest_database_target_invalid")
    if not isinstance(normalized["release_id"], str) or not normalized["release_id"]:
        raise StagingReleaseBindingError("manifest_release_id_invalid")
    for field in ("commit", "tree"):
        if not isinstance(normalized[field], str) or not _HEX40.fullmatch(normalized[field]):
            raise StagingReleaseBindingError("manifest_revision_invalid")
    if not isinstance(normalized["image_repository"], str) or not normalized["image_repository"]:
        raise StagingReleaseBindingError("manifest_image_repository_invalid")
    if not isinstance(normalized["image_digest"], str) or not _IMAGE_DIGEST.fullmatch(normalized["image_digest"]):
        raise StagingReleaseBindingError("manifest_image_digest_invalid")
    if not isinstance(normalized["manifest_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", normalized["manifest_hash"]):
        raise StagingReleaseBindingError("manifest_hash_invalid")
    unsigned = {key: normalized[key] for key in MANIFEST_FIELDS if key != "manifest_hash"}
    calculated = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if calculated != normalized["manifest_hash"]:
        raise StagingReleaseBindingError("manifest_hash_mismatch")
    created = _parse_time(normalized["created_at"], "created_at")
    expires = _parse_time(normalized["expires_at"], "expires_at")
    if expires <= created:
        raise StagingReleaseBindingError("manifest_expiry_invalid")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if require_active and expires <= current:
        raise StagingReleaseBindingError("manifest_expired")
    return normalized


def _binding_paths() -> tuple[Path, Path]:
    manifest = os.getenv("SENTINEL_DNA_RELEASE_BINDING_MANIFEST_FILE", "").strip()
    trust = os.getenv("SENTINEL_DNA_RELEASE_BINDING_TRUST_FILE", "").strip()
    if not manifest or not trust:
        raise StagingReleaseBindingError("external_release_binding_required")
    return Path(manifest), Path(trust)


def load_release_binding_document(*, now: datetime | None = None) -> dict[str, Any]:
    manifest_path, trust_path = _binding_paths()
    manifest = validate_release_binding(_read_json(manifest_path, "manifest"), now=now)
    trust = _read_json(trust_path, "trusted_binding")
    if set(trust) != TRUST_FIELDS or trust["schema_version"] != SCHEMA_VERSION:
        raise StagingReleaseBindingError("trusted_binding_fields_invalid")
    if any(not isinstance(trust[field], str) for field in TRUST_FIELDS - {"schema_version"}):
        raise StagingReleaseBindingError("trusted_binding_fields_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", trust["manifest_hash"]) or not _IMAGE_DIGEST.fullmatch(trust["image_digest"]):
        raise StagingReleaseBindingError("trusted_binding_fields_invalid")
    if any(trust[field] != manifest[field] for field in ("manifest_hash", "commit", "tree", "image_digest")):
        raise StagingReleaseBindingError("trusted_binding_mismatch")
    return manifest


def load_release_binding(*, now: datetime | None = None) -> dict[str, str]:
    manifest = load_release_binding_document(now=now)
    return {
        "application_commit": manifest["commit"],
        "repository_tree": manifest["tree"],
        "image_digest": manifest["image_digest"],
        "environment": manifest["environment"],
        "database_target_identity": manifest["database_target_identity"],
        "release_binding_manifest_hash": manifest["manifest_hash"],
    }


__all__ = ["DATABASE_TARGET", "ENVIRONMENT", "REPOSITORY", "SCHEMA_VERSION", "StagingReleaseBindingError", "load_release_binding", "load_release_binding_document", "validate_release_binding"]
