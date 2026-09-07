from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_provider_json_without_independent_verifier_is_blocked() -> None:
    module = _load("gate4_verify_second_remediation", ROOT / "deployment/staging/scripts/verify_gate4_release_manifest.py")
    evidence = {
        "status": "VERIFIED",
        "subject_digest": "sha256:" + "a" * 64,
        "signer_identity": "test-signer",
        "issuer": "test-issuer",
        "transparency_reference": "test-transparency",
        "revocation_status": "ACTIVE",
        "verification_reference": "test-reference",
        "verified_at": "2026-01-01T00:00:00Z",
        "verification_method_identity": "provider",
        "verification_method_version": "1",
    }
    try:
        module.UnavailableEvidenceVerifier().verify(evidence, evidence["subject_digest"])
    except module.ManifestError as exc:
        assert str(exc) == "cryptographic_evidence_verifier_unavailable"
    else:
        raise AssertionError("self-attested provider JSON must not authorize")


def test_production_custody_mode_blocks_without_external_verifier() -> None:
    module = _load("gate4_custody_second_remediation", ROOT / "deployment/staging/scripts/validate_gate4_external_custody.py")
    result = module.validate(
        {},
        expected_commit="a" * 40,
        expected_tree="b" * 40,
        require_external_verification=True,
    )
    assert result["status"] == "BLOCKED"
    assert "cryptographic_evidence_verifier:unavailable" in result["errors"]


def test_workflow_has_snapshot_and_no_sequential_terminal_promotion() -> None:
    workflow = (ROOT / ".github/workflows/gate4-custody.yml").read_text(encoding="utf-8")
    assert "ACTIVATION_INSTANCE_SNAPSHOT" in workflow
    assert "staging and terminal publication locations must be distinct" in workflow
    assert "Block terminal publication pending atomic release-reference authority" in workflow
    assert "docker buildx imagetools create" not in workflow
