"""Generate a non-signing, read-only staging provenance observation manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from tools.artifact_provenance import (
    ProvenanceError, TrustBoundary, VerificationStatus, build_manifest,
    inspect_artifact, inspect_dependency_closure, validate_digest,
)

BRIDGE_ENV = "SENTINEL_DNA_BROWSER_AUTH_BRIDGE"


def _source_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _artifact(path: Path, kind: str) -> dict:
    try:
        return {"status": VerificationStatus.VERIFIED.value, **inspect_artifact(path, kind=kind)}
    except ProvenanceError as exc:
        return {"status": VerificationStatus.MISMATCHED.value, "path": str(path), "error": str(exc)}


def _historical_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError("historical_manifest_unavailable") from exc
    if not isinstance(value, dict):
        raise ProvenanceError("historical_manifest_invalid")
    required = ("approved_runtime_module_digest", "staging_origin", "provider_identity", "runtime_module_identity")
    if any(not value.get(key) for key in required):
        raise ProvenanceError("historical_manifest_missing_required_field")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-path", required=True, type=Path)
    parser.add_argument("--lockfile-path", required=True, type=Path)
    parser.add_argument("--historical-manifest", required=True, type=Path)
    parser.add_argument("--historical-lockfile-digest", required=True)
    parser.add_argument("--historical-image-reference", required=True)
    parser.add_argument("--historical-image-digest", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    historical = _historical_manifest(args.historical_manifest)
    historical_runtime_digest = validate_digest(historical["approved_runtime_module_digest"], "historical_runtime_digest")
    historical_lockfile_digest = validate_digest(args.historical_lockfile_digest, "historical_lockfile_digest")
    historical_image_digest = validate_digest(args.historical_image_digest, "historical_image_digest")
    blockers: list[str] = []
    runtime = _artifact(args.runtime_path, "approved_playwright_runtime")
    lockfile = _artifact(args.lockfile_path, "dependency_lockfile")
    if runtime.get("sha256") != historical_runtime_digest:
        blockers.append("runtime_digest_differs_from_historical_custody_manifest")
    if lockfile.get("sha256") != historical_lockfile_digest:
        blockers.append("lockfile_digest_differs_from_historical_reference")
    try:
        dependency_closure = inspect_dependency_closure(args.runtime_path)
    except ProvenanceError as exc:
        dependency_closure = {"status": VerificationStatus.MISMATCHED.value, "error": str(exc)}
    if dependency_closure.get("status") != VerificationStatus.VERIFIED.value:
        blockers.append("dependency_closure_not_complete")
    provider_identity = str(historical["provider_identity"])
    runtime_identity = str(historical["runtime_module_identity"])
    runtime["provider_identity"] = provider_identity
    runtime["runtime_identity"] = runtime_identity
    runtime["playwright_version"] = next((item.get("version") for item in dependency_closure.get("packages", []) if item.get("name") == "playwright"), None)

    configured_bridge = os.environ.get(BRIDGE_ENV)
    if configured_bridge:
        bridge = _artifact(Path(configured_bridge), "browser_auth_bridge")
        bridge["identity"] = None
        bridge["identity_source"] = "caller_supplied"
        bridge["status"] = VerificationStatus.UNVERIFIED.value
        blockers.append("bridge_identity_is_caller_supplied")
    else:
        bridge = {"status": VerificationStatus.UNVERIFIED.value, "identity": None, "identity_source": "not_configured", "path": None}
        blockers.append("browser_auth_bridge_not_configured")

    image = {
        "status": VerificationStatus.UNVERIFIED.value,
        "image_reference": args.historical_image_reference,
        "immutable_image_digest": historical_image_digest,
        "registry": None,
        "repository": args.historical_image_reference.split(":", 1)[0],
        "manifest_digest": None,
        "platform": None,
        "source": "historical_rehearsal_evidence_only",
        "independent_verification": False,
    }
    blockers.extend(["image_is_historical_not_current_candidate", "image_independent_verification_unavailable"])
    status = VerificationStatus.MISMATCHED.value if "runtime_digest_differs_from_historical_custody_manifest" in blockers else VerificationStatus.UNVERIFIED.value
    manifest = build_manifest(
        runtime=runtime, lockfile=lockfile, bridge=bridge, image=image, source_commit=_source_commit(),
        provider_identity=provider_identity, runtime_identity=runtime_identity,
        certified_origin=str(historical["staging_origin"]), dependency_closure=dependency_closure,
        verification_status=status, trust_boundary=TrustBoundary.LOCAL_OBSERVED.value,
        verifier_identity="local-provenance-observer", verification_timestamp=datetime.now(timezone.utc).isoformat(),
        blockers=blockers,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    print(args.output)
    print(manifest["manifest_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
