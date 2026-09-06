"""Fail-closed artifact, dependency, bridge, and OCI provenance primitives.

This module is deliberately independent of Gate 5 activation and deployment
validators.  It records observations and verifies supplied provenance
evidence; it never treats a syntactically valid digest as independent proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any, Mapping


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPARSE_POINT = 0x400


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    MISMATCHED = "MISMATCHED"


class TrustBoundary(StrEnum):
    LOCAL_OBSERVED = "LOCAL_OBSERVED"
    LOCAL_VERIFIED = "LOCAL_VERIFIED"
    EXTERNALLY_VERIFIED = "EXTERNALLY_VERIFIED"
    INDEPENDENTLY_CERTIFIED = "INDEPENDENTLY_CERTIFIED"


class ProvenanceError(ValueError):
    pass


def canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(canonicalize(value), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def validate_digest(value: Any, field: str = "digest") -> str:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value.lower()):
        raise ProvenanceError(f"{field}_malformed")
    return value.lower()


def _is_reparse(path: Path) -> bool:
    try:
        stat_result = os.lstat(path)
    except OSError as exc:
        raise ProvenanceError("artifact_unavailable") from exc
    if os.path.islink(path):
        return True
    return bool(getattr(stat_result, "st_file_attributes", 0) & REPARSE_POINT)


def _reject_reparse_components(path: Path) -> None:
    current = Path(path.anchor) if path.anchor else Path()
    for component in path.parts[1:] if path.anchor else path.parts:
        current = current / component
        if _is_reparse(current):
            raise ProvenanceError("path_reparse_point_rejected")


def _stable_read(path: Path) -> tuple[bytes, os.stat_result, str]:
    if not path.is_absolute():
        raise ProvenanceError("artifact_path_must_be_absolute")
    _reject_reparse_components(path)
    try:
        resolved = Path(os.path.realpath(path))
        if resolved != path:
            raise ProvenanceError("path_substitution_detected")
        before = os.stat(path, follow_symlinks=False)
        with open(path, "rb") as handle:
            opened = os.fstat(handle.fileno())
            content = handle.read()
            after = os.fstat(handle.fileno())
        final = os.stat(path, follow_symlinks=False)
    except ProvenanceError:
        raise
    except OSError as exc:
        raise ProvenanceError("artifact_unavailable") from exc
    identities = (before.st_ino, opened.st_ino, after.st_ino, final.st_ino)
    sizes = (before.st_size, opened.st_size, after.st_size, final.st_size)
    if len(set(identities)) != 1 or len(set(sizes)) != 1:
        raise ProvenanceError("artifact_changed_during_hash")
    return content, final, str(resolved)


def inspect_artifact(path: str | os.PathLike[str], *, kind: str, expected_digest: str | None = None) -> dict[str, Any]:
    artifact_path = Path(path)
    content, stat_result, resolved_path = _stable_read(artifact_path)
    digest = sha256_bytes(content)
    if expected_digest is not None and digest != validate_digest(expected_digest, f"{kind}_expected_digest"):
        raise ProvenanceError(f"{kind}_digest_mismatch")
    modified = datetime.fromtimestamp(stat_result.st_mtime, timezone.utc).isoformat()
    return {
        "kind": kind,
        "absolute_path": str(artifact_path),
        "resolved_real_path": resolved_path,
        "sha256": digest,
        "byte_length": len(content),
        "file_type": mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream",
        "reparse_point": False,
        "symlink": False,
        "modified_at": modified,
        "content_address": digest,
    }


def _package_lock_metadata(lock: Mapping[str, Any]) -> dict[str, Any]:
    root = lock.get("packages", {}).get("")
    if not isinstance(root, Mapping):
        raise ProvenanceError("lockfile_root_missing")
    return {
        "lockfile_version": lock.get("lockfileVersion"),
        "requires": lock.get("requires"),
        "package_manager": root.get("packageManager"),
        "engines": root.get("engines"),
    }


def inspect_dependency_closure(runtime_path: str | os.PathLike[str]) -> dict[str, Any]:
    runtime = Path(runtime_path)
    if not runtime.is_absolute():
        raise ProvenanceError("runtime_path_must_be_absolute")
    root = runtime.parent
    package_path = root / "package.json"
    lock_path = root / "package-lock.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError("dependency_metadata_unavailable") from exc
    if package.get("private") is not True or lock.get("lockfileVersion") != 3:
        raise ProvenanceError("dependency_metadata_invalid")
    lock_packages = lock.get("packages")
    if not isinstance(lock_packages, dict):
        raise ProvenanceError("lockfile_packages_missing")
    root_entry = lock_packages.get("") or {}
    direct = dict(package.get("dependencies") or {})
    direct.update(package.get("optionalDependencies") or {})
    pending = list(direct)
    visited: set[str] = set()
    closure: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    while pending:
        name = pending.pop(0)
        if name in visited:
            continue
        visited.add(name)
        lock_key = f"node_modules/{name}"
        entry = lock_packages.get(lock_key)
        if not isinstance(entry, Mapping):
            unresolved.append({"package": name, "reason": "lock_entry_missing"})
            continue
        record = {"path": lock_key, "name": name, "version": entry.get("version"), "resolved": entry.get("resolved"), "integrity": entry.get("integrity"), "dependencies": entry.get("dependencies") or {}, "optionalDependencies": entry.get("optionalDependencies") or {}, "os": entry.get("os"), "cpu": entry.get("cpu")}
        if not record["version"]:
            unresolved.append({"package": name, "reason": "version_missing"})
        if not record["integrity"] and not record["link"]:
            unresolved.append({"package": name, "reason": "integrity_missing"})
        installed = root / "node_modules" / Path(name)
        installed_manifest = installed / "package.json"
        if installed_manifest.exists():
            try:
                installed_data = json.loads(installed_manifest.read_text(encoding="utf-8"))
                if installed_data.get("name") != name or installed_data.get("version") != entry.get("version"):
                    unresolved.append({"package": name, "reason": "installed_version_mismatch"})
            except (OSError, json.JSONDecodeError):
                unresolved.append({"package": name, "reason": "installed_manifest_invalid"})
        elif not (set(entry.get("os") or ()) - {platform.system().lower()}) and not entry.get("optional"):
            unresolved.append({"package": name, "reason": "installed_package_missing"})
        for child in list((entry.get("dependencies") or {}).keys()) + list((entry.get("optionalDependencies") or {}).keys()):
            pending.append(child)
        closure.append(record)
    closure.sort(key=lambda item: item["path"])
    closure_digest = sha256_bytes(canonical_bytes(closure))
    lock_observation = inspect_artifact(lock_path, kind="dependency_lockfile")
    return {"status": VerificationStatus.VERIFIED.value if not unresolved else VerificationStatus.MISMATCHED.value, "direct_dependencies": sorted(direct), "packages": closure, "unresolved": unresolved, "closure_digest": closure_digest, "lockfile": lock_observation, "metadata": _package_lock_metadata(lock)}


def verify_oci_evidence(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    if not evidence:
        return {"status": VerificationStatus.UNVERIFIED.value, "reasons": ["provenance_missing"]}
    reference = evidence.get("image_reference")
    digest = evidence.get("immutable_image_digest")
    if not isinstance(reference, str) or "@sha256:" not in reference:
        return {"status": VerificationStatus.MISMATCHED.value, "reasons": ["mutable_image_reference"]}
    try:
        digest = validate_digest(digest, "immutable_image_digest")
    except ProvenanceError as exc:
        return {"status": VerificationStatus.MISMATCHED.value, "reasons": [str(exc)]}
    if not reference.endswith("@" + digest):
        return {"status": VerificationStatus.MISMATCHED.value, "reasons": ["image_digest_mismatch"]}
    if evidence.get("revoked"):
        return {"status": VerificationStatus.REVOKED.value, "reasons": ["provenance_revoked"]}
    expires = evidence.get("expires_at")
    if expires and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
        return {"status": VerificationStatus.EXPIRED.value, "reasons": ["provenance_expired"]}
    required = ("source_repository", "source_commit", "build_identity", "builder_identity", "build_timestamp", "environment", "attestation_reference", "attestation_digest", "verification_result", "verifier_identity", "verification_timestamp")
    missing = [field for field in required if not evidence.get(field)]
    if missing or evidence.get("verification_result") != "VERIFIED" or evidence.get("verifier_identity_source") != "trusted_metadata":
        return {"status": VerificationStatus.UNVERIFIED.value, "reasons": (["provenance_fields_missing"] if missing else []) + (["verifier_identity_not_trusted"] if evidence.get("verifier_identity_source") != "trusted_metadata" else [])}
    try:
        validate_digest(evidence.get("attestation_digest"), "attestation_digest")
    except ProvenanceError:
        return {"status": VerificationStatus.MISMATCHED.value, "reasons": ["attestation_digest_malformed"]}
    return {"status": VerificationStatus.VERIFIED.value, "reasons": []}


def verify_source_binding(*, source_commit: str | None, build_identity: str | None, image_digest: str | None, attestation_digest: str | None, custody_binding: Mapping[str, Any] | None) -> dict[str, Any]:
    if not custody_binding:
        return {"status": VerificationStatus.UNVERIFIED.value, "reasons": ["custody_binding_missing"]}
    fields = {"source_commit": source_commit, "build_identity": build_identity, "image_digest": image_digest, "attestation_digest": attestation_digest}
    mismatches = [key for key, value in fields.items() if value is None or custody_binding.get(key) != value]
    return {"status": VerificationStatus.MISMATCHED.value if mismatches else VerificationStatus.VERIFIED.value, "reasons": [f"{key}_mismatch" for key in mismatches]}


def build_manifest(*, runtime: Mapping[str, Any], lockfile: Mapping[str, Any], bridge: Mapping[str, Any] | None, image: Mapping[str, Any] | None, source_commit: str | None, provider_identity: str, runtime_identity: str, certified_origin: str, dependency_closure: Mapping[str, Any], verification_status: str, trust_boundary: str, verifier_identity: str, verification_timestamp: str, blockers: list[str]) -> dict[str, Any]:
    body = {"schema_version": "1.0", "milestone": "artifact_image_provenance", "runtime": runtime, "lockfile": lockfile, "bridge": bridge, "image": image, "source_commit": source_commit, "provider_identity": provider_identity, "runtime_identity": runtime_identity, "certified_origin": certified_origin, "dependency_closure": dependency_closure, "verification_status": verification_status, "trust_boundary": trust_boundary, "verifier_identity": verifier_identity, "verification_timestamp": verification_timestamp, "blockers": sorted(set(blockers))}
    body["manifest_sha256"] = sha256_bytes(canonical_bytes(body))
    return body


__all__ = ["DIGEST_RE", "ProvenanceError", "VerificationStatus", "TrustBoundary", "build_manifest", "canonical_bytes", "canonicalize", "inspect_artifact", "inspect_dependency_closure", "sha256_bytes", "validate_digest", "verify_oci_evidence", "verify_source_binding"]
