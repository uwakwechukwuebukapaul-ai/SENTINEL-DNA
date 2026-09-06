import copy
import hashlib
import json
from pathlib import Path

from deployment.staging.scripts.validate_gate4_external_custody import validate

RELEASE_COMMIT = "8cf91fe0736f5da4521687272ffb10d1dfa0779b"
RELEASE_TREE = "6cf6b210d8a052da92e4b76feafe14247ce1d8bf"
ROOT = Path(__file__).parents[2]


def digest(letter): return "sha256:" + letter * 64


def record(letter="e"):
    return {"status": "INDEPENDENTLY_APPROVED", "evidence_reference": f"custody:evidence:{letter}", "evidence_digest": digest(letter), "verifier_identity": "external-verifier:test-only", "verification_method": "test-only-independent-record", "verified_at": "2026-09-06T00:00:00Z", "approval_reference": "approval:test-only"}


def signature(value, signer):
    return {"status": "INDEPENDENTLY_APPROVED", "artifact_digest": value, "signer_identity": signer, "oidc_issuer": "https://issuer.example.test", "transparency_log_reference": "rekor:test-only", "verification_record": record("f")}


def attestation(value, bound=True):
    return {"status": "INDEPENDENTLY_APPROVED", "subject_digest": value, "reference": "attestation:test-only", "predicate_type": "https://slsa.dev/provenance/v1", "source_repository": "https://example.test/sentinel-dna", "source_commit": RELEASE_COMMIT if bound else "1" * 40, "source_tree": RELEASE_TREE if bound else "2" * 40, "builder_identity": "builder:test-only", "workflow_identity": "workflow:test-only", "build_timestamp": "2026-09-06T00:00:00Z", "platform": "linux/amd64", "materials": ["material:test-only"], "verification_record": record("a")}


def sbom(value): return {"status": "INDEPENDENTLY_APPROVED", "format": "SPDX", "document_reference": "sbom:test-only", "document_digest": digest("b"), "artifact_digest": value, "verification_record": record("c")}


def image(name, letter, artifact_class="SENTINEL_BUILT"):
    value = digest(letter)
    external = artifact_class == "EXTERNAL_SECURITY_BOUNDARY"
    third_party = artifact_class == "THIRD_PARTY"
    signer = "signer:external" if external else "signer:vendor" if third_party else "signer:custom"
    return {"artifact_class": artifact_class, "supplier_identity": "external-gateway-owner" if external else "vendor-owner" if third_party else "sentinel-dna", "reference": f"registry.example.test/{name}@{value}", "digest": value, "platform": "linux/amd64", "registry": "registry.example.test", "source_commit": ("1" * 40) if (external or third_party) else RELEASE_COMMIT, "source_tree": ("2" * 40) if (external or third_party) else RELEASE_TREE, "signature": signature(value, signer), "attestation": attestation(value, not (external or third_party)), "sbom": sbom(value)}


def activation(fields):
    base = {"schema_version": "1.0", "provider_identity": "provider:test-only", "runtime_module_identity": "runtime:test-only", "approved_runtime_module_digest": fields["approved_runtime_module_digest"], "approved_image_runtime_digest": fields["trusted_browser_image_digest"], "approved_runtime_dependency_lockfile_digest": fields["approved_runtime_dependency_lockfile_digest"], "approved_browser_auth_bridge_identity": "bridge:test-only", "approved_browser_auth_bridge_digest": fields["approved_browser_auth_bridge_digest"], "release_commit": RELEASE_COMMIT, "release_tree": RELEASE_TREE, "application_image_digest": fields["application_image_digest"], "trusted_browser_image_digest": fields["trusted_browser_image_digest"], "egress_gateway_image_digest": fields["egress_gateway_image_digest"], "edge_image_digest": fields["edge_image_digest"], "postgres_image_digest": fields["postgres_image_digest"], "redis_image_digest": fields["redis_image_digest"], "approved_browser_executable_digest": fields["approved_browser_executable_digest"], "approved_browser_revision": "synthetic-revision", "approved_browser_version": "synthetic-version", "approved_browser_base_image_digest": fields["approved_browser_base_image_digest"], "approved_egress_policy_reference": "policy:test-only", "approved_egress_policy_digest": fields["approved_egress_policy_digest"], "release_approval_reference": "approval:release:test-only", "registry_identity": "registry.example.test", "signature_evidence_status": "INDEPENDENTLY_APPROVED", "attestation_evidence_status": "INDEPENDENTLY_APPROVED", "sbom_evidence_status": "INDEPENDENTLY_APPROVED", "staging_origin": "https://synthetic.example.test", "activation_timestamp": "2026-09-06T00:00:00Z", "operator_approval_reference": "approval:test-only"}
    base.update({"egress_gateway_artifact_class": "EXTERNAL_SECURITY_BOUNDARY", "edge_artifact_class": "EXTERNAL_SECURITY_BOUNDARY", "approved_edge_configuration_digest": fields["approved_edge_configuration_digest"], "approved_edge_tls_custody_reference": "tls-custody:test-only", "approved_edge_tls_certificate_digest": fields["approved_edge_tls_certificate_digest"], "approved_edge_tls_private_key_custody_reference": "tls-key-custody:test-only", "approved_edge_tls_certificate_key_match_evidence_digest": fields["approved_edge_tls_certificate_key_match_evidence_digest"]})
    canonical = {k: base[k] for k in sorted(base)}
    base["integrity"] = {"algorithm": "sha256", "manifest_hash": hashlib.sha256(json.dumps(canonical, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()}
    return base


def complete_package(tmp_path):
    artifacts = {"application_image": image("application", "a"), "trusted_browser_image": image("browser", "b"), "egress_gateway_image": image("gateway", "c", "EXTERNAL_SECURITY_BOUNDARY"), "edge_image": image("edge", "d", "EXTERNAL_SECURITY_BOUNDARY"), "postgres_image": image("postgres", "e", "THIRD_PARTY"), "redis_image": image("redis", "f", "THIRD_PARTY")}
    artifacts["playwright_runtime"] = {"digest": digest("1"), "lockfile_digest": digest("2"), "platform": "linux/amd64", "signature": signature(digest("1"), "signer:custom"), "attestation": attestation(digest("1"))}
    artifacts["browser_executable"] = {"digest": digest("3"), "revision": "synthetic-revision", "version": "synthetic-version", "platform": "linux/amd64", "base_image_digest": digest("4"), "signature": signature(digest("3"), "signer:custom"), "attestation": attestation(digest("3"))}
    artifacts["browserauth_bridge"] = {"digest": digest("5"), "evidence_reference": "bridge:test-only", "export_contract": "requestBrowserAuth", "structural_validation": "PASS", "approval_reference": "approval:bridge:test-only", "signature": signature(digest("5"), "signer:custom"), "verification_record": record("5")}
    artifacts["egress_policy"] = {"reference": "policy:test-only", "digest": digest("6"), "owner": "owner:test-only", "reviewer": "reviewer:test-only", "approved_at": "2026-09-06T00:00:00Z", "review_by": "2026-10-06T00:00:00Z", "approval_reference": "approval:policy:test-only", "signature": signature(digest("6"), "signer:custom"), "verification_record": record("6")}
    artifacts["edge_configuration"] = {"artifact_class": "REPOSITORY_CONFIGURATION", "reference": "config:deployment/staging/nginx.conf", "digest": digest("8"), "source_commit": RELEASE_COMMIT, "source_tree": RELEASE_TREE, "verification_record": record("8")}
    artifacts["edge_tls"] = {"artifact_class": "EXTERNAL_TLS_CUSTODY", "custody_reference": "tls-custody:test-only", "certificate_digest": digest("9"), "private_key_custody_reference": "tls-key-custody:test-only", "certificate_key_match": {"status": "INDEPENDENTLY_APPROVED", "certificate_digest": digest("9"), "private_key_custody_reference": "tls-key-custody:test-only", "evidence_reference": "tls-key-match:test-only", "evidence_digest": digest("a"), "verifier_identity": "verifier:tls:test-only", "verification_method": "independent-cert-key-match", "verified_at": "2026-09-06T00:00:00Z", "approval_reference": "approval:tls-key-match:test-only"}, "verification_record": record("9")}
    fields = {"application_image_digest": artifacts["application_image"]["digest"], "trusted_browser_image_digest": artifacts["trusted_browser_image"]["digest"], "egress_gateway_image_digest": artifacts["egress_gateway_image"]["digest"], "edge_image_digest": artifacts["edge_image"]["digest"], "postgres_image_digest": artifacts["postgres_image"]["digest"], "redis_image_digest": artifacts["redis_image"]["digest"], "approved_runtime_module_digest": artifacts["playwright_runtime"]["digest"], "approved_runtime_dependency_lockfile_digest": artifacts["playwright_runtime"]["lockfile_digest"], "approved_browser_executable_digest": artifacts["browser_executable"]["digest"], "approved_browser_base_image_digest": artifacts["browser_executable"]["base_image_digest"], "approved_browser_auth_bridge_digest": artifacts["browserauth_bridge"]["digest"], "approved_egress_policy_digest": artifacts["egress_policy"]["digest"], "approved_edge_configuration_digest": artifacts["edge_configuration"]["digest"], "approved_edge_tls_certificate_digest": artifacts["edge_tls"]["certificate_digest"], "approved_edge_tls_certificate_key_match_evidence_digest": artifacts["edge_tls"]["certificate_key_match"]["evidence_digest"]}
    manifest = activation(fields); manifest_path = tmp_path / "activation.json"; raw = json.dumps(manifest, separators=(",", ":")).encode(); manifest_path.write_bytes(raw)
    activation_artifact = {"digest": "sha256:" + hashlib.sha256(raw).hexdigest(), "reference": "activation:test-only", "manifest_bytes_reference": "activation:test-only", "signature": signature("sha256:" + hashlib.sha256(raw).hexdigest(), "signer:custom"), "verification_record": record("7")}
    artifacts["activation_manifest"] = activation_artifact
    package = {"schema_version": "3.0", "release": {"commit": RELEASE_COMMIT, "tree": RELEASE_TREE}, "artifacts": artifacts, "trust_policies": {"sentinel_built_images": {"supplier_identity": "sentinel-dna", "signer_identity": "signer:custom", "registry_identity": "registry.example.test", "policy_reference": "policy:custom", "status": "INDEPENDENTLY_APPROVED", "verification_record": record("8")}, "external_security_boundary_images": {"supplier_identity": "external-gateway-owner", "signer_identity": "signer:external", "registry_identity": "registry.example.test", "policy_reference": "policy:external", "status": "INDEPENDENTLY_APPROVED", "verification_record": record("9")}, "third_party_images": {"supplier_identity": "vendor-owner", "signer_identity": "signer:vendor", "registry_identity": "registry.example.test", "policy_reference": "policy:vendor", "status": "INDEPENDENTLY_APPROVED", "verification_record": record("0")}}, "verification": {"status": "INDEPENDENTLY_APPROVED", "registry_identity": "registry.example.test", "independent_verifier": "verifier:test-only", "verification_record": record("1")}}
    return package, manifest_path


def check(package, manifest_path): return validate(package, expected_commit=RELEASE_COMMIT, expected_tree=RELEASE_TREE, activation_manifest_path=manifest_path)


def test_complete_package_requires_actual_manifest_and_passes(tmp_path):
    package, manifest = complete_package(tmp_path); result = check(package, manifest); assert result["status"] == "PASS"


def test_self_asserted_booleans_are_not_accepted(tmp_path):
    package, manifest = complete_package(tmp_path); package["verification"]["signatures_verified"] = True; package["artifacts"]["application_image"]["signature"]["status"] = "CLAIMED"; assert check(package, manifest)["status"] == "BLOCKED"


def test_missing_actual_manifest_bytes_blocks(tmp_path):
    package, _ = complete_package(tmp_path); assert check(package, None)["status"] == "BLOCKED"


def test_manifest_digest_and_cross_binding_fail_closed(tmp_path):
    package, manifest = complete_package(tmp_path); package["artifacts"]["activation_manifest"]["digest"] = digest("9"); assert check(package, manifest)["status"] == "BLOCKED"
    package, manifest = complete_package(tmp_path); data = json.loads(manifest.read_text()); data["release_tree"] = "1" * 40; manifest.write_text(json.dumps(data)); assert check(package, manifest)["status"] == "BLOCKED"


def test_unknown_schema_field_is_rejected(tmp_path):
    package, manifest = complete_package(tmp_path); package["unexpected"] = True; result = check(package, manifest); assert result["status"] == "BLOCKED"; assert any("unknown" in e for e in result["errors"])


def test_unreadable_or_malformed_schema_blocks(tmp_path):
    package, manifest = complete_package(tmp_path); schema = tmp_path / "schema.json"; schema.write_text("{not-json}"); result = validate(package, expected_commit=RELEASE_COMMIT, expected_tree=RELEASE_TREE, schema_path=schema, activation_manifest_path=manifest); assert result["status"] == "BLOCKED"; assert "schema:unreadable_or_invalid" in result["errors"]


def test_false_evidence_and_mismatches_block(tmp_path):
    package, manifest = complete_package(tmp_path); package["artifacts"]["browser_executable"]["signature"]["verification_record"]["status"] = "CLAIMED"; package["artifacts"]["egress_policy"]["digest"] = digest("0"); package["artifacts"]["egress_policy"]["signature"]["artifact_digest"] = digest("0"); package["artifacts"]["application_image"]["reference"] = "registry.example.test/app:tag"; result = check(package, manifest); assert result["status"] == "BLOCKED"


def test_third_party_signer_must_be_separate(tmp_path):
    package, manifest = complete_package(tmp_path); package["artifacts"]["redis_image"]["signature"]["signer_identity"] = "signer:custom"; assert check(package, manifest)["status"] == "BLOCKED"


def test_historical_and_conflicting_statuses_never_promote(tmp_path):
    package, manifest = complete_package(tmp_path); package["artifacts"]["trusted_browser_image"]["signature"]["status"] = "HISTORICAL"; package["artifacts"]["browserauth_bridge"]["verification_record"]["status"] = "CONFLICTING"; assert check(package, manifest)["status"] == "BLOCKED"


def test_authoritative_release_constants_are_used():
    assert RELEASE_COMMIT == "8cf91fe0736f5da4521687272ffb10d1dfa0779b"; assert RELEASE_TREE == "6cf6b210d8a052da92e4b76feafe14247ce1d8bf"


def test_external_artifacts_are_not_sentinel_bound(tmp_path):
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["egress_gateway_image"]["source_commit"] = RELEASE_COMMIT
    assert check(package, manifest)["status"] == "BLOCKED"


def test_external_artifact_requires_supplier_identity(tmp_path):
    package, manifest = complete_package(tmp_path)
    del package["artifacts"]["edge_image"]["supplier_identity"]
    assert check(package, manifest)["status"] == "BLOCKED"


def test_supplier_identity_must_match_approved_trust_policy(tmp_path):
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["edge_image"]["supplier_identity"] = "unapproved-label"
    assert check(package, manifest)["status"] == "BLOCKED"


def test_external_artifact_requires_immutable_reference(tmp_path):
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["edge_image"]["reference"] = "registry.example.test/edge:latest"
    assert check(package, manifest)["status"] == "BLOCKED"


def test_external_artifact_requires_independent_signature_sbom_and_provenance(tmp_path):
    for field in ("signature", "sbom", "attestation"):
        package, manifest = complete_package(tmp_path)
        package["artifacts"]["egress_gateway_image"][field] = None
        assert check(package, manifest)["status"] == "BLOCKED"


def test_external_artifact_historical_or_conflicting_evidence_blocks(tmp_path):
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["edge_image"]["signature"]["verification_record"]["status"] = "HISTORICAL"
    assert check(package, manifest)["status"] == "BLOCKED"


def test_activation_external_digest_and_egress_policy_mismatch_blocks(tmp_path):
    package, manifest = complete_package(tmp_path)
    data = json.loads(manifest.read_text())
    data["edge_image_digest"] = digest("0")
    manifest.write_text(json.dumps(data))
    assert check(package, manifest)["status"] == "BLOCKED"
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["egress_policy"]["digest"] = digest("0")
    assert check(package, manifest)["status"] == "BLOCKED"


def test_sentinel_built_artifact_requires_release_binding(tmp_path):
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["application_image"]["source_tree"] = "1" * 40
    assert check(package, manifest)["status"] == "BLOCKED"


def test_edge_configuration_and_tls_custody_are_required(tmp_path):
    package, manifest = complete_package(tmp_path)
    del package["artifacts"]["edge_configuration"]
    assert check(package, manifest)["status"] == "BLOCKED"
    package, manifest = complete_package(tmp_path)
    del package["artifacts"]["edge_tls"]
    assert check(package, manifest)["status"] == "BLOCKED"


def test_tls_requires_private_key_custody_reference(tmp_path):
    package, manifest = complete_package(tmp_path)
    del package["artifacts"]["edge_tls"]["private_key_custody_reference"]
    assert check(package, manifest)["status"] == "BLOCKED"


def test_tls_requires_independent_certificate_key_match(tmp_path):
    package, manifest = complete_package(tmp_path)
    del package["artifacts"]["edge_tls"]["certificate_key_match"]
    assert check(package, manifest)["status"] == "BLOCKED"
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["edge_tls"]["certificate_key_match"]["status"] = "CLAIMED"
    assert check(package, manifest)["status"] == "BLOCKED"


def test_tls_rejects_mismatched_certificate_key_evidence(tmp_path):
    package, manifest = complete_package(tmp_path)
    package["artifacts"]["edge_tls"]["certificate_key_match"]["certificate_digest"] = digest("0")
    assert check(package, manifest)["status"] == "BLOCKED"


def test_tls_activation_binding_rejects_mismatch(tmp_path):
    package, manifest = complete_package(tmp_path)
    data = json.loads(manifest.read_text())
    data["approved_edge_tls_certificate_key_match_evidence_digest"] = digest("0")
    manifest.write_text(json.dumps(data))
    assert check(package, manifest)["status"] == "BLOCKED"
