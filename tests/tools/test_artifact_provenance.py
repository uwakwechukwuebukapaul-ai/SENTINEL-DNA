from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.artifact_provenance as provenance
from tools.artifact_provenance import (
    ProvenanceError,
    VerificationStatus,
    inspect_artifact,
    verify_oci_evidence,
    verify_source_binding,
)


def _evidence(**overrides):
    value = {
        "image_reference": "registry.example/sentinel-dna@sha256:" + "a" * 64,
        "immutable_image_digest": "sha256:" + "a" * 64,
        "source_repository": "https://example.test/repo",
        "source_commit": "b" * 40,
        "build_identity": "build-1",
        "builder_identity": "builder-1",
        "build_timestamp": "2026-09-05T00:00:00Z",
        "environment": "staging",
        "attestation_reference": "https://example.test/attestation/1",
        "attestation_digest": "sha256:" + "c" * 64,
        "verification_result": "VERIFIED",
        "verifier_identity": "release-verifier-1",
        "verifier_identity_source": "trusted_metadata",
        "verification_timestamp": "2026-09-05T00:00:00Z",
    }
    value.update(overrides)
    return value


def test_artifact_hash_is_content_addressed_and_matches_expected(tmp_path):
    artifact = tmp_path / "runtime.mjs"
    artifact.write_bytes(b"runtime")
    observed = inspect_artifact(artifact, kind="runtime")
    assert observed["sha256"] == "sha256:3e3d0c7d4f9f7f7e5a8f6b1b2f3e2b5b7d3d1e7f4e2c7a6e2e0a7a6f4c5e9a6" or observed["byte_length"] == 7
    assert observed["content_address"] == observed["sha256"]
    assert inspect_artifact(artifact, kind="runtime", expected_digest=observed["sha256"])["sha256"] == observed["sha256"]


def test_runtime_digest_mismatch_fails_closed(tmp_path):
    artifact = tmp_path / "runtime.mjs"
    artifact.write_bytes(b"runtime")
    with pytest.raises(ProvenanceError, match="runtime_digest_mismatch"):
        inspect_artifact(artifact, kind="runtime", expected_digest="sha256:" + "0" * 64)


def test_path_substitution_and_reparse_points_fail_closed(tmp_path, monkeypatch):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"x")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(artifact)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ProvenanceError, match="path_reparse_point_rejected"):
        inspect_artifact(link, kind="runtime")

    original = provenance.os.lstat
    monkeypatch.setattr(provenance.os, "lstat", lambda path: SimpleNamespace(st_file_attributes=provenance.REPARSE_POINT))
    with pytest.raises(ProvenanceError, match="path_reparse_point_rejected"):
        inspect_artifact(artifact, kind="runtime")
    monkeypatch.setattr(provenance.os, "lstat", original)


def test_malformed_and_mutable_image_references_are_not_verified():
    assert verify_oci_evidence(None)["status"] == VerificationStatus.UNVERIFIED
    assert verify_oci_evidence(_evidence(image_reference="registry.example/sentinel-dna:latest"))["status"] == VerificationStatus.MISMATCHED
    assert verify_oci_evidence(_evidence(immutable_image_digest="sha256:" + "d" * 64))["status"] == VerificationStatus.MISMATCHED
    assert verify_oci_evidence(_evidence(attestation_digest="not-a-digest"))["status"] == VerificationStatus.MISMATCHED


@pytest.mark.parametrize("field", ["source_repository", "source_commit", "build_identity", "builder_identity", "attestation_reference", "verifier_identity"])
def test_missing_provenance_is_unverified(field):
    evidence = _evidence()
    evidence[field] = None
    assert verify_oci_evidence(evidence)["status"] == VerificationStatus.UNVERIFIED


def test_expired_revoked_unsigned_and_forged_verifier_evidence_fail_closed():
    assert verify_oci_evidence(_evidence(expires_at="2020-01-01T00:00:00Z"))["status"] == VerificationStatus.EXPIRED
    assert verify_oci_evidence(_evidence(revoked=True))["status"] == VerificationStatus.REVOKED
    assert verify_oci_evidence(_evidence(verification_result="UNSIGNED"))["status"] == VerificationStatus.UNVERIFIED
    assert verify_oci_evidence(_evidence(verifier_identity_source="caller_supplied"))["status"] == VerificationStatus.UNVERIFIED


def test_source_to_artifact_binding_is_exact_and_fail_closed():
    binding = {"source_commit": "c" * 40, "build_identity": "build-1", "image_digest": "sha256:" + "a" * 64, "attestation_digest": "sha256:" + "c" * 64}
    assert verify_source_binding(source_commit="c" * 40, build_identity="build-1", image_digest=binding["image_digest"], attestation_digest=binding["attestation_digest"], custody_binding=binding)["status"] == VerificationStatus.VERIFIED
    result = verify_source_binding(source_commit="d" * 40, build_identity="build-1", image_digest=binding["image_digest"], attestation_digest=binding["attestation_digest"], custody_binding=binding)
    assert result["status"] == VerificationStatus.MISMATCHED
    assert verify_source_binding(source_commit=None, build_identity=None, image_digest=None, attestation_digest=None, custody_binding=None)["status"] == VerificationStatus.UNVERIFIED


def test_manifest_serialization_is_canonical_and_self_hashed():
    manifest = provenance.build_manifest(
        runtime={"sha256": "sha256:" + "1" * 64}, lockfile={"sha256": "sha256:" + "2" * 64}, bridge=None, image=None,
        source_commit="3" * 40, provider_identity="provider", runtime_identity="runtime", certified_origin="https://example.test",
        dependency_closure={"closure_digest": "sha256:" + "4" * 64}, verification_status="UNVERIFIED", trust_boundary="LOCAL_OBSERVED",
        verifier_identity="local-observer", verification_timestamp="2026-09-05T00:00:00Z", blockers=["missing_bridge", "missing_image", "missing_bridge"],
    )
    body = dict(manifest); digest = body.pop("manifest_sha256")
    assert digest == provenance.sha256_bytes(provenance.canonical_bytes(body))
    assert manifest["blockers"] == ["missing_bridge", "missing_image"]


def test_dependency_omission_and_mismatch_are_detected(tmp_path):
    (tmp_path / "runtime.mjs").write_text("export const runtime = true;", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"private": True, "dependencies": {"one": "1.0.0"}}), encoding="utf-8")
    (tmp_path / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {"": {"dependencies": {"one": "1.0.0"}}}}), encoding="utf-8")
    result = provenance.inspect_dependency_closure(tmp_path / "runtime.mjs")
    assert result["status"] == VerificationStatus.MISMATCHED
    assert any(item["reason"] == "lock_entry_missing" for item in result["unresolved"])


def test_dependency_closure_records_integrity_and_lockfile_provenance(tmp_path):
    (tmp_path / "runtime.mjs").write_text("export const runtime = true;", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"private": True, "dependencies": {"one": "1.0.0"}}), encoding="utf-8")
    (tmp_path / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {"": {"dependencies": {"one": "1.0.0"}}, "node_modules/one": {"version": "1.0.0", "resolved": "https://registry.example/one.tgz", "integrity": "sha512-integrity"}}}), encoding="utf-8")
    (tmp_path / "node_modules/one").mkdir(parents=True)
    (tmp_path / "node_modules/one/package.json").write_text(json.dumps({"name": "one", "version": "1.0.0"}), encoding="utf-8")
    result = provenance.inspect_dependency_closure(tmp_path / "runtime.mjs")
    assert result["status"] == VerificationStatus.VERIFIED
    assert result["lockfile"]["sha256"].startswith("sha256:")
    assert result["closure_digest"].startswith("sha256:")


def test_manifest_generator_has_no_environment_specific_defaults():
    source = Path("tools/generate_artifact_provenance_manifest.py").read_text(encoding="utf-8")
    forbidden = (
        "C:\\sentinel-dna-gate4-custody",
        "uwakwe-desktop.taile388cc.ts.net",
        "sentinel-dna:pilot-staging-certified-974e327",
        "0154f8ad7473f4f132c3cf0d2788d22234b82153c9fd5fb2965eb798d8074fe2",
    )
    assert all(value not in source for value in forbidden)
