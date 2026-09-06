"""Fail-closed Gate4 signed release-manifest boundary.

This module deliberately separates cryptographic signature validation from signer
trust validation. Production signature and status providers are injected; the
default providers fail closed because production trust infrastructure is not
part of this repository change.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

SCHEMA_VERSION = "gate4.release-manifest.v1"
ACTIVATION_PATH = "deployment/staging/scripts/trusted_browser_activation_manifest.mjs"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FORBIDDEN_KEY_RE = re.compile(r"(?:secret|password|credential|private[_-]?key|token)", re.I)
MUTABLE_IMAGE_RE = re.compile(r"(?:^|/)[^/@\s]+:[^/@\s]+$")
ARRAY_SORT_KEYS = {
    "artifacts.sentinel_built_images": "identity",
    "artifacts.external_boundary_images": "identity",
    "artifacts.third_party_images": "identity",
    "artifacts.provenance": "identity",
}


class ManifestError(ValueError):
    pass


class SignatureValidator(Protocol):
    def verify(self, payload: bytes, envelope: dict[str, Any]) -> "SignatureResult": ...


class StatusProvider(Protocol):
    def status(self, manifest_digest: str, signer_identity: str) -> str: ...


@dataclass(frozen=True)
class SignatureResult:
    valid: bool
    signer_identity: str
    issuer: str
    transparency_reference: str


class UnavailableSignatureValidator:
    def verify(self, payload: bytes, envelope: dict[str, Any]) -> SignatureResult:
        raise ManifestError("signature_validation_provider_unavailable")


class UnavailableStatusProvider:
    def status(self, manifest_digest: str, signer_identity: str) -> str:
        raise ManifestError("revocation_status_provider_unavailable")


def _reject_forbidden_keys(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if FORBIDDEN_KEY_RE.search(key):
                raise ManifestError(f"{path}.{key}:forbidden_secret_field")
            _reject_forbidden_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_keys(item, f"{path}[{index}]")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        raise ManifestError(f"{path}:numeric_values_forbidden")


def _reject_unknown_keys(value: Any, allowed: dict[str, set[str]], path: str = "manifest") -> None:
    if isinstance(value, dict):
        permitted = allowed.get(path) or allowed.get(re.sub(r"\[\d+\]", "[]", path))
        if permitted is not None:
            unknown = set(value) - permitted
            if unknown:
                raise ManifestError(f"{path}.{sorted(unknown)[0]}:unknown_field")
        for key, item in value.items():
            child = f"{path}.{key}"
            _reject_unknown_keys(item, allowed, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_unknown_keys(item, allowed, f"{path}[{index}]")


def _normalise_arrays(value: Any, path: str = "", key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {name: _normalise_arrays(item, f"{path}.{name}".strip("."), name) for name, item in value.items()}
    if isinstance(value, list):
        items = [_normalise_arrays(item, path) for item in value]
        key = ARRAY_SORT_KEYS.get(path)
        if key:
            if any(not isinstance(item, dict) or not isinstance(item.get(key), str) for item in items):
                raise ManifestError(f"{path}:deterministic_sort_key_required")
            return sorted(items, key=lambda item: item[key])
        return items
    if isinstance(value, str) and key and key.endswith("_at"):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ManifestError(f"{path}:timestamp_invalid") from exc
        if parsed.tzinfo is None:
            raise ManifestError(f"{path}:timestamp_timezone_required")
        return parsed.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def canonical_bytes(manifest: dict[str, Any]) -> bytes:
    if not isinstance(manifest, dict):
        raise ManifestError("manifest:object_required")
    _reject_forbidden_keys(manifest)
    normalized = _normalise_arrays(copy.deepcopy(manifest))
    return json.dumps(normalized, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_digest(manifest_or_bytes: dict[str, Any] | bytes) -> str:
    payload = canonical_bytes(manifest_or_bytes) if isinstance(manifest_or_bytes, dict) else manifest_or_bytes
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _require(value: Any, path: str) -> None:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{path}:required")


def _digest(value: Any, path: str) -> None:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise ManifestError(f"{path}:sha256_required")


def _image(item: Any, path: str, commit: str | None, tree: str | None, external: bool) -> None:
    if not isinstance(item, dict):
        raise ManifestError(f"{path}:object_required")
    for key in ("identity", "supplier", "signer"):
        _require(item.get(key), f"{path}.{key}")
    if MUTABLE_IMAGE_RE.search(item["identity"]):
        raise ManifestError(f"{path}.identity:mutable_image_reference")
    _digest(item.get("digest"), f"{path}.digest")
    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        raise ManifestError(f"{path}.provenance:required")
    _require(provenance.get("identity"), f"{path}.provenance.identity")
    _digest(provenance.get("digest"), f"{path}.provenance.digest")
    if external and ("source_commit" in item or "source_tree" in item):
        raise ManifestError(f"{path}:external_source_binding_forbidden")
    if not external and (item.get("source_commit") != commit or item.get("source_tree") != tree):
        raise ManifestError(f"{path}:source_binding_mismatch")


def validate_manifest_structure(manifest: dict[str, Any]) -> None:
    allowed = {
        "manifest": {"schema_version", "release_id", "repository", "commit_sha", "tree_sha", "activation_manifest", "custody_package", "artifacts", "target_platform", "created_at", "expires_at", "status", "revocation_status_reference", "supersedes_release_id"},
        "manifest.repository": {"owner", "name", "full_name", "repository_id"},
        "manifest.activation_manifest": {"path", "sha256"},
        "manifest.custody_package": {"identity", "digest"},
        "manifest.artifacts": {"sentinel_built_images", "external_boundary_images", "third_party_images", "trusted_browser", "egress_policy", "tls_certified_origin", "browserauth", "sbom", "provenance", "deployment"},
        "manifest.artifacts.sentinel_built_images[]": {"identity", "digest", "source_commit", "source_tree", "supplier", "signer", "provenance"},
        "manifest.artifacts.external_boundary_images[]": {"identity", "digest", "supplier", "signer", "provenance"},
        "manifest.artifacts.third_party_images[]": {"identity", "digest", "supplier", "signer", "provenance"},
        "manifest.artifacts.trusted_browser": {"image", "playwright_version", "browser_revision", "browser_version", "executable"},
        "manifest.artifacts.trusted_browser.image": {"identity", "digest"},
        "manifest.artifacts.trusted_browser.executable": {"identity", "digest"},
        "manifest.artifacts.egress_policy": {"identity", "digest"},
        "manifest.artifacts.tls_certified_origin": {"identity", "digest"},
        "manifest.artifacts.browserauth": {"identity", "digest"},
        "manifest.artifacts.sbom": {"identity", "digest"},
        "manifest.artifacts.provenance[]": {"identity", "digest"},
        "manifest.artifacts.deployment": {"identity", "digest"},
        "manifest.artifacts.sentinel_built_images[].provenance": {"identity", "digest"},
        "manifest.artifacts.external_boundary_images[].provenance": {"identity", "digest"},
        "manifest.artifacts.third_party_images[].provenance": {"identity", "digest"},
    }
    _reject_unknown_keys(manifest, allowed)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError("schema_version:unsupported")
    for key in ("release_id", "commit_sha", "tree_sha", "created_at", "expires_at"):
        _require(manifest.get(key), key)
    commit, tree = manifest["commit_sha"], manifest["tree_sha"]
    if not COMMIT_RE.fullmatch(commit) or not COMMIT_RE.fullmatch(tree):
        raise ManifestError("release_identity:malformed")
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        raise ManifestError("repository:required")
    for key in ("owner", "name", "full_name", "repository_id"):
        _require(repository.get(key), f"repository.{key}")
    if repository["full_name"] != f"{repository['owner']}/{repository['name']}":
        raise ManifestError("repository.full_name:mismatch")
    activation = manifest.get("activation_manifest")
    if not isinstance(activation, dict) or activation.get("path") != ACTIVATION_PATH:
        raise ManifestError("activation_manifest.path:authoritative_path_required")
    _digest(activation.get("sha256"), "activation_manifest.sha256")
    package = manifest.get("custody_package")
    if not isinstance(package, dict):
        raise ManifestError("custody_package:required")
    _require(package.get("identity"), "custody_package.identity")
    _digest(package.get("digest"), "custody_package.digest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ManifestError("artifacts:required")
    for name in ("sentinel_built_images", "external_boundary_images", "third_party_images"):
        items = artifacts.get(name)
        if not isinstance(items, list) or not items:
            raise ManifestError(f"artifacts.{name}:required")
        for index, item in enumerate(items):
            _image(item, f"artifacts.{name}[{index}]", commit, tree, name != "sentinel_built_images")
    browser = artifacts.get("trusted_browser")
    if not isinstance(browser, dict):
        raise ManifestError("artifacts.trusted_browser:required")
    for key in ("playwright_version", "browser_revision", "browser_version"):
        _require(browser.get(key), f"artifacts.trusted_browser.{key}")
    for key in ("image", "executable"):
        item = browser.get(key)
        if not isinstance(item, dict):
            raise ManifestError(f"artifacts.trusted_browser.{key}:required")
        _require(item.get("identity"), f"artifacts.trusted_browser.{key}.identity")
        _digest(item.get("digest"), f"artifacts.trusted_browser.{key}.digest")
        if key == "image" and MUTABLE_IMAGE_RE.search(item["identity"]):
            raise ManifestError(f"artifacts.trusted_browser.{key}.identity:mutable_image_reference")
    for name in ("egress_policy", "tls_certified_origin", "browserauth", "sbom", "deployment"):
        item = artifacts.get(name)
        if not isinstance(item, dict):
            raise ManifestError(f"artifacts.{name}:required")
        _require(item.get("identity"), f"artifacts.{name}.identity")
        _digest(item.get("digest"), f"artifacts.{name}.digest")
    provenance = artifacts.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        raise ManifestError("artifacts.provenance:required")
    for index, item in enumerate(provenance):
        _require(item.get("identity") if isinstance(item, dict) else None, f"artifacts.provenance[{index}].identity")
        _digest(item.get("digest") if isinstance(item, dict) else None, f"artifacts.provenance[{index}].digest")
    if manifest.get("status") != "ACTIVE":
        raise ManifestError("status:not_active")
    if not UTC_RE.fullmatch(manifest["created_at"]) or not UTC_RE.fullmatch(manifest["expires_at"]):
        raise ManifestError("timestamps:utc_required")
    if "revocation_status_reference" not in manifest:
        raise ManifestError("revocation_status_reference:required")


def load_canonical_manifest(path: Path, supplied_digest: str) -> tuple[dict[str, Any], bytes, str]:
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("manifest:invalid_json_or_encoding") from exc
    canonical = canonical_bytes(manifest)
    computed = manifest_digest(canonical)
    if supplied_digest != computed:
        raise ManifestError("manifest_digest:mismatch")
    if raw != canonical:
        raise ManifestError("manifest:noncanonical_bytes")
    normalized_manifest = json.loads(canonical.decode("utf-8"))
    validate_manifest_structure(normalized_manifest)
    return normalized_manifest, canonical, computed


def validate_detached_signature(payload: bytes, envelope: dict[str, Any], validator: SignatureValidator, trust_policy: dict[str, Any]) -> SignatureResult:
    if not isinstance(envelope, dict) or envelope.get("scheme") != "dsse":
        raise ManifestError("signature_envelope:dsse_required")
    if envelope.get("payload_type") != "application/vnd.gate4.release-manifest.v1+json":
        raise ManifestError("signature_envelope:payload_type_mismatch")
    signature = envelope.get("signature")
    if not isinstance(signature, str):
        raise ManifestError("signature_envelope:signature_required")
    try:
        base64.b64decode(signature, validate=True)
    except Exception as exc:
        raise ManifestError("signature_envelope:signature_encoding_invalid") from exc
    result = validator.verify(payload, envelope)
    if not result.valid:
        raise ManifestError("signature:invalid")
    if result.signer_identity != trust_policy.get("trusted_signer_identity"):
        raise ManifestError("signer_trust:identity_mismatch")
    if result.issuer != trust_policy.get("trusted_issuer"):
        raise ManifestError("signer_trust:issuer_mismatch")
    if trust_policy.get("require_transparency", True) and not result.transparency_reference:
        raise ManifestError("signer_trust:transparency_required")
    return result


def authorize_release(*, manifest_path: Path, manifest_digest_input: str, signature_path: Path, repository: str, head_sha: str, tree_sha: str, activation_path: Path, validator: SignatureValidator | None = None, status_provider: StatusProvider | None = None, trust_policy: dict[str, Any] | None = None, now: datetime | None = None) -> dict[str, str]:
    manifest, canonical, digest = verify_manifest_authority(manifest_path=manifest_path, manifest_digest_input=manifest_digest_input, signature_path=signature_path, repository=repository, validator=validator, status_provider=status_provider, trust_policy=trust_policy, now=now)
    if head_sha != manifest["commit_sha"]:
        raise ManifestError("HEAD:manifest_commit_mismatch")
    if tree_sha != manifest["tree_sha"]:
        raise ManifestError("HEAD_tree:manifest_tree_mismatch")
    if str(activation_path).replace("\\", "/") != ACTIVATION_PATH:
        raise ManifestError("activation_path:authoritative_path_required")
    actual_activation = "sha256:" + hashlib.sha256(activation_path.read_bytes()).hexdigest()
    if actual_activation != manifest["activation_manifest"]["sha256"]:
        raise ManifestError("activation_manifest:digest_mismatch")
    return {"manifest_digest": digest, "release_id": manifest["release_id"], "commit_sha": manifest["commit_sha"], "tree_sha": manifest["tree_sha"], "signer_identity": manifest["_verified_signer_identity"]}


def verify_manifest_authority(*, manifest_path: Path, manifest_digest_input: str, signature_path: Path, repository: str, validator: SignatureValidator | None = None, status_provider: StatusProvider | None = None, trust_policy: dict[str, Any] | None = None, now: datetime | None = None) -> tuple[dict[str, Any], bytes, str]:
    manifest, canonical, digest = load_canonical_manifest(manifest_path, manifest_digest_input)
    envelope = json.loads(signature_path.read_text(encoding="utf-8"))
    policy = trust_policy or {}
    result = validate_detached_signature(canonical, envelope, validator or UnavailableSignatureValidator(), policy)
    status = (status_provider or UnavailableStatusProvider()).status(digest, result.signer_identity)
    if status != "ACTIVE":
        raise ManifestError("manifest_status:not_active")
    now_value = now or datetime.now(timezone.utc)
    expires = datetime.strptime(manifest["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if now_value >= expires:
        raise ManifestError("manifest:expired")
    if manifest["repository"]["full_name"] != repository:
        raise ManifestError("repository:mismatch")
    manifest = dict(manifest)
    manifest["_verified_signer_identity"] = result.signer_identity
    return manifest, canonical, digest


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Verify a Gate4 signed release manifest")
    parser.add_argument("manifest")
    parser.add_argument("--digest", required=True)
    parser.add_argument("--signature", required=True)
    parser.add_argument("--trust-policy")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--head")
    parser.add_argument("--tree")
    parser.add_argument("--activation")
    args = parser.parse_args()
    try:
        trust_policy = json.loads(Path(args.trust_policy).read_text(encoding="utf-8")) if args.trust_policy else {}
        if not isinstance(trust_policy, dict):
            raise ManifestError("trust_policy:object_required")
        if not args.head or not args.tree or not args.activation:
            manifest, _, digest = verify_manifest_authority(manifest_path=Path(args.manifest), manifest_digest_input=args.digest, signature_path=Path(args.signature), repository=args.repository, trust_policy=trust_policy)
            result = {"manifest_digest": digest, "release_id": manifest["release_id"], "commit_sha": manifest["commit_sha"], "tree_sha": manifest["tree_sha"]}
        else:
            result = authorize_release(manifest_path=Path(args.manifest), manifest_digest_input=args.digest, signature_path=Path(args.signature), repository=args.repository, head_sha=args.head, tree_sha=args.tree, activation_path=Path(args.activation), trust_policy=trust_policy)
    except (ManifestError, OSError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
