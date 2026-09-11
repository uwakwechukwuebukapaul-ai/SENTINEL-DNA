from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from deployment.staging.scripts.verify_gate4_release_manifest import (
    ACTIVATION_PATH,
    ManifestError,
    SignatureResult,
    authorize_release,
    canonical_bytes,
    manifest_digest,
    validate_manifest_structure,
    build_gate4_request,
    canonical_protocol_bytes,
    verify_authenticated_response,
    _ed25519_verify,
    EvidenceBytes,
    AuthorityAttestation,
    ReplayDecision,
    UnavailableEvidenceRetriever,
    UnavailableReplayAuthority,
    verify_independent_evidence,
    ExternalSignatureValidator,
)


COMMIT = "a" * 40
TREE = "b" * 40
DIGEST = lambda letter: "sha256:" + letter * 64


def _identity(name: str, letter: str) -> dict[str, str]:
    return {"identity": name, "digest": DIGEST(letter)}


def _image(name: str, letter: str, *, external: bool = False) -> dict:
    value = {
        "identity": name,
        "digest": DIGEST(letter),
        "supplier": "external-supplier" if external else "sentinel-dna",
        "signer": "external-signer" if external else "sentinel-signer",
        "provenance": _identity(f"provenance:{name}", letter),
    }
    if not external:
        value.update(source_commit=COMMIT, source_tree=TREE)
    return value


def valid_manifest() -> dict:
    validator_digest = "sha256:" + __import__("hashlib").sha256(Path(ACTIVATION_PATH).read_bytes()).hexdigest()
    instance_digest = "sha256:" + __import__("hashlib").sha256(b"external-activation-instance-test-only").hexdigest()
    return {
        "schema_version": "gate4.release-manifest.v1",
        "release_id": "gate4-test-release",
        "repository": {"owner": "uwakwechukwuebukpaul-ai", "name": "SENTINEL-DNA", "full_name": "uwakwechukwuebukpaul-ai/SENTINEL-DNA", "repository_id": "123456"},
        "commit_sha": COMMIT,
        "tree_sha": TREE,
        "activation_manifest": {"validator_path": ACTIVATION_PATH, "validator_sha256": validator_digest, "instance_reference": "external-custody:test-only", "instance_sha256": instance_digest},
        "custody_package": _identity("custody-package:gate4-test", "c"),
        "artifacts": {
            "sentinel_built_images": [_image("application", "d")],
            "external_boundary_images": [_image("edge", "e", external=True), _image("egress", "f", external=True)],
            "third_party_images": [_image("postgres", "1", external=True), _image("redis", "2", external=True)],
            "trusted_browser": {"image": _identity("trusted-browser", "3"), "playwright_version": "1.62.1", "browser_revision": "test-revision", "browser_version": "test-version", "executable": _identity("browser-executable", "4")},
            "egress_policy": _identity("egress-policy:test", "5"),
            "tls_certified_origin": _identity("tls-origin:test", "6"),
            "browserauth": _identity("browserauth:test", "7"),
            "sbom": _identity("sbom:test", "8"),
            "provenance": [_identity("provenance:release", "9")],
            "deployment": _identity("deployment:test", "a"),
        },
        "target_platform": "linux/amd64",
        "created_at": "2026-09-06T00:00:00Z",
        "expires_at": "2027-09-06T00:00:00Z",
        "status": "ACTIVE",
        "revocation_status_reference": "status:test-release",
    }


class GoodSignature:
    def verify(self, payload: bytes, envelope: dict) -> SignatureResult:
        assert payload == canonical_bytes(valid_manifest())
        return SignatureResult(True, "release-signer:test", "https://issuer.test", "rekor:test")


class ActiveStatus:
    def status(self, manifest_digest: str, signer_identity: str) -> str:
        return "ACTIVE"


class InvalidSignature:
    def verify(self, payload: bytes, envelope: dict) -> SignatureResult:
        return SignatureResult(False, "release-signer:test", "https://issuer.test", "rekor:test")


class UnknownSigner:
    def verify(self, payload: bytes, envelope: dict) -> SignatureResult:
        return SignatureResult(True, "unknown-signer", "https://issuer.test", "rekor:test")


class RevokedStatus:
    def status(self, manifest_digest: str, signer_identity: str) -> str:
        return "REVOKED"


def _signature(path: Path) -> None:
    path.write_text(json.dumps({"scheme": "dsse", "payload_type": "application/vnd.gate4.release-manifest.v1+json", "signature": "AQ=="}, separators=(",", ":")), encoding="utf-8")


def test_schema_and_canonical_digest_are_deterministic():
    value = valid_manifest()
    validate_manifest_structure(value)
    reordered = copy.deepcopy(value)
    reordered["artifacts"]["external_boundary_images"].reverse()
    reordered = {key: reordered[key] for key in reversed(list(reordered))}
    assert canonical_bytes(value) == canonical_bytes(reordered)
    assert manifest_digest(value) == manifest_digest(reordered)


def test_unicode_and_timestamp_normalization_are_canonical():
    value = valid_manifest()
    value["release_id"] = "gate4-é"
    value["created_at"] = "2026-09-06T01:00:00+01:00"
    normalized = copy.deepcopy(value)
    normalized["created_at"] = "2026-09-06T00:00:00Z"
    assert canonical_bytes(value) == canonical_bytes(normalized)


@pytest.mark.parametrize("mutator", [
    lambda value: value.update(commit_sha=COMMIT[:-1]),
    lambda value: value.update(status="SUPERSEDED"),
    lambda value: value["activation_manifest"].update(validator_path="deployment/staging/trusted_browser_activation_manifest.json"),
    lambda value: value["artifacts"]["sentinel_built_images"][0].update(source_tree="c" * 40),
    lambda value: value["artifacts"]["external_boundary_images"][0].update(source_commit=COMMIT),
    lambda value: value["artifacts"]["sentinel_built_images"][0].update(identity="registry.example.test/application:latest"),
    lambda value: value["artifacts"].update(unexpected={}),
    lambda value: value.update(target_platform=1.5),
])
def test_invalid_release_manifest_is_fail_closed(mutator):
    value = valid_manifest()
    mutator(value)
    if value.get("target_platform") == 1.5:
        with pytest.raises(ManifestError, match="numeric_values_forbidden"):
            canonical_bytes(value)
    else:
        with pytest.raises(ManifestError):
            validate_manifest_structure(value)


def test_authorization_requires_signature_and_status_and_binds_source(tmp_path):
    value = valid_manifest()
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_bytes(canonical_bytes(value))
    signature_path = tmp_path / "release-manifest.sig.json"
    _signature(signature_path)
    instance_path = tmp_path / "external-activation.json"
    instance_path.write_bytes(b"external-activation-instance-test-only")
    result = authorize_release(
        manifest_path=manifest_path,
        manifest_digest_input=manifest_digest(value),
        signature_path=signature_path,
        repository="uwakwechukwuebukpaul-ai/SENTINEL-DNA",
        head_sha=COMMIT,
        tree_sha=TREE,
        validator_path=Path(ACTIVATION_PATH),
        activation_instance_path=instance_path,
        validator=GoodSignature(),
        status_provider=ActiveStatus(),
        trust_policy={"trusted_signer_identity": "release-signer:test", "trusted_issuer": "https://issuer.test", "require_transparency": True},
        now=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )
    assert result["commit_sha"] == COMMIT


@pytest.mark.parametrize("validator,status_provider,expected", [
    (InvalidSignature(), ActiveStatus(), "signature:invalid"),
    (UnknownSigner(), ActiveStatus(), "signer_trust:identity_mismatch"),
    (GoodSignature(), RevokedStatus(), "manifest_status:not_active"),
])
def test_signature_and_status_authority_are_separate_fail_closed_boundaries(tmp_path, validator, status_provider, expected):
    value = valid_manifest()
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_bytes(canonical_bytes(value))
    signature_path = tmp_path / "release-manifest.sig.json"
    _signature(signature_path)
    instance_path = tmp_path / "external-activation.json"
    instance_path.write_bytes(b"external-activation-instance-test-only")
    with pytest.raises(ManifestError, match=expected):
        authorize_release(manifest_path=manifest_path, manifest_digest_input=manifest_digest(value), signature_path=signature_path, repository="uwakwechukwuebukpaul-ai/SENTINEL-DNA", head_sha=COMMIT, tree_sha=TREE, validator_path=Path(ACTIVATION_PATH), activation_instance_path=instance_path, validator=validator, status_provider=status_provider, trust_policy={"trusted_signer_identity": "release-signer:test", "trusted_issuer": "https://issuer.test", "require_transparency": True}, now=datetime(2026, 9, 6, tzinfo=timezone.utc))


def test_noncanonical_transport_bytes_are_rejected(tmp_path):
    value = valid_manifest()
    path = tmp_path / "release-manifest.json"
    path.write_bytes(canonical_bytes(value) + b"\n")
    with pytest.raises(ManifestError, match="noncanonical_bytes"):
        from deployment.staging.scripts.verify_gate4_release_manifest import load_canonical_manifest
        load_canonical_manifest(path, manifest_digest(value))


def test_duplicate_json_keys_are_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_bytes(b'{"schema_version":"gate4.release-manifest.v1","schema_version":"gate4.release-manifest.v1"}')
    with pytest.raises(ManifestError, match="duplicate_key"):
        from deployment.staging.scripts.verify_gate4_release_manifest import load_canonical_manifest
        load_canonical_manifest(path, "sha256:" + "0" * 64)


@pytest.mark.parametrize("field", ["manifest_digest_input", "head_sha", "tree_sha"])
def test_arbitrary_transport_substitution_is_rejected(tmp_path, field):
    value = valid_manifest()
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_bytes(canonical_bytes(value))
    signature_path = tmp_path / "release-manifest.sig.json"
    _signature(signature_path)
    instance_path = tmp_path / "external-activation.json"
    instance_path.write_bytes(b"external-activation-instance-test-only")
    kwargs = {"manifest_digest_input": manifest_digest(value), "head_sha": COMMIT, "tree_sha": TREE}
    kwargs[field] = "c" * (64 if field == "manifest_digest_input" else 40) if field != "manifest_digest_input" else DIGEST("c")
    with pytest.raises(ManifestError):
        authorize_release(manifest_path=manifest_path, signature_path=signature_path, manifest_digest_input=kwargs["manifest_digest_input"], repository="uwakwechukwuebukpaul-ai/SENTINEL-DNA", head_sha=kwargs["head_sha"], tree_sha=kwargs["tree_sha"], validator_path=Path(ACTIVATION_PATH), activation_instance_path=instance_path, validator=GoodSignature(), status_provider=ActiveStatus(), trust_policy={"trusted_signer_identity": "release-signer:test", "trusted_issuer": "https://issuer.test", "require_transparency": True}, now=datetime(2026, 9, 6, tzinfo=timezone.utc))


def test_protocol_request_is_canonical_and_nonce_is_256_bits():
    candidate = {"commit_sha": COMMIT, "tree_sha": TREE, "sentinel_image_digests": [DIGEST("a")], "external_boundary_image_digests": [DIGEST("b")], "third_party_image_digests": [DIGEST("c")], "runtime_digest": DIGEST("d"), "lockfile_digest": DIGEST("e"), "browser_executable_digest": DIGEST("f"), "browser_base_image_digest": DIGEST("1"), "browserauth_bridge_digest": DIGEST("2"), "activation_manifest_digest": DIGEST("3"), "edge_configuration_digest": DIGEST("4"), "tls_evidence_digest": DIGEST("5"), "custody_package_digest": DIGEST("6"), "release_manifest_digest": DIGEST("7")}
    request = build_gate4_request(operation="EvidenceVerifier.verify", subject_digest=DIGEST("a"), candidate=candidate)
    assert len(request["nonce"]) == 32
    assert request["request_hash"] == "sha256:" + __import__("hashlib").sha256(canonical_protocol_bytes({key: request[key] for key in request if key != "request_hash"})).hexdigest()
    assert canonical_protocol_bytes(request) == canonical_protocol_bytes({key: request[key] for key in reversed(request)})


def test_protocol_response_mismatch_and_missing_trust_root_block():
    candidate = {"commit_sha": COMMIT, "tree_sha": TREE, "sentinel_image_digests": [DIGEST("a")], "external_boundary_image_digests": [DIGEST("b")], "third_party_image_digests": [DIGEST("c")], "runtime_digest": DIGEST("d"), "lockfile_digest": DIGEST("e"), "browser_executable_digest": DIGEST("f"), "browser_base_image_digest": DIGEST("1"), "browserauth_bridge_digest": DIGEST("2"), "activation_manifest_digest": DIGEST("3"), "edge_configuration_digest": DIGEST("4"), "tls_evidence_digest": DIGEST("5"), "custody_package_digest": DIGEST("6"), "release_manifest_digest": DIGEST("7")}
    request = build_gate4_request(operation="EvidenceVerifier.verify", subject_digest=DIGEST("a"), candidate=candidate)
    response = {"protocol_version": "sentinel-dna.gate4.authenticated-response.v1", "operation": request["operation"], "request_id": request["request_id"], "nonce": request["nonce"], "request_hash": "sha256:" + "0" * 64, "subject_digest": request["subject_digest"], "candidate": request["candidate"], "evidence_reference": "evidence://external/object?digest=" + DIGEST("b"), "evidence_digest": DIGEST("b"), "provider_identity": "external", "provider_version": "v1", "verifier_identity": "external-verifier", "verification_method_identity": "external-method", "verification_method_version": "v1", "verified_at": "2026-09-07T00:00:00Z", "expires_at": "2026-09-07T00:10:00Z", "revocation_status": "ACTIVE", "approval_reference": "approval:external", "transparency_reference": "transparency:external", "decision": "APPROVED", "denial_code": "", "signature_algorithm": "Ed25519", "signing_key_id": "key-1", "trust_root_reference": "trust-root:external", "identity_claims": {}, "signature": "AA=="}
    with pytest.raises(ManifestError, match="request_binding_mismatch"):
        verify_authenticated_response(response, request, trust_root={}, replay_authority=UnavailableReplayAuthority())


def test_ed25519_verifier_matches_rfc8032_empty_message_vector():
    public_key = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    signature = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155" "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert _ed25519_verify(public_key, signature, b"")


class TestReplayAuthority:
    def __init__(self, decision): self.decision = decision; self.calls = []; self.attestation = AuthorityAttestation("authority", True, True, "config:external", "auth:external")
    def consume(self, **kwargs): self.calls.append(kwargs); return self.decision


class TestEvidenceRetriever:
    def __init__(self, result): self.result = result; self.attestation = AuthorityAttestation("retriever", True, True, "config:external", "auth:external")
    def retrieve(self, reference): return self.result


class TestRevocationAuthority:
    def __init__(self, result=True): self.result = result; self.attestation = AuthorityAttestation("revocation", True, True, "config:external", "auth:external")
    def verify(self, response): return self.result


class TestTransparencyAuthority:
    def __init__(self, result=True): self.result = result; self.attestation = AuthorityAttestation("transparency", True, True, "config:external", "auth:external")
    def verify(self, response): return self.result


class TestIdentityAuthority:
    def __init__(self, claims): self.claims = claims; self.attestation = AuthorityAttestation("identity", True, True, "config:external", "auth:external")
    def verify(self, claims): return self.claims


def _protocol_candidate():
    return {"commit_sha": COMMIT, "tree_sha": TREE, "sentinel_image_digests": [DIGEST("a")], "external_boundary_image_digests": [DIGEST("b")], "third_party_image_digests": [DIGEST("c")], "runtime_digest": DIGEST("d"), "lockfile_digest": DIGEST("e"), "browser_executable_digest": DIGEST("f"), "browser_base_image_digest": DIGEST("1"), "browserauth_bridge_digest": DIGEST("2"), "activation_manifest_digest": DIGEST("3"), "edge_configuration_digest": DIGEST("4"), "tls_evidence_digest": DIGEST("5"), "custody_package_digest": DIGEST("6"), "release_manifest_digest": DIGEST("7")}


def _protocol_response_case():
    request = build_gate4_request(operation="EvidenceVerifier.verify", subject_digest=DIGEST("a"), candidate=_protocol_candidate())
    evidence_digest = "sha256:" + __import__("hashlib").sha256(b"evidence").hexdigest()
    reference = "evidence://external/object?digest=" + evidence_digest
    claims = {key: f"{key}:external" for key in {"sentinel_dna", "requester", "builder", "signer", "verifier", "approver", "runtime_provider", "evidence_producer", "evidence_retriever", "cryptographic_verifier", "release_authority"}}
    response = {"protocol_version": "sentinel-dna.gate4.authenticated-response.v1", "operation": request["operation"], "request_id": request["request_id"], "nonce": request["nonce"], "request_hash": request["request_hash"], "subject_digest": request["subject_digest"], "candidate": request["candidate"], "evidence_reference": reference, "evidence_digest": evidence_digest, "provider_identity": "provider", "provider_version": "v1", "verifier_identity": "verifier:external", "verification_method_identity": "method:external", "verification_method_version": "v1", "verified_at": "2026-09-07T00:00:00Z", "expires_at": "2026-09-07T00:10:00Z", "revocation_status": "ACTIVE", "approval_reference": "approval:external", "transparency_reference": "transparency:external", "decision": "APPROVED", "denial_code": "", "signature_algorithm": "Ed25519", "signing_key_id": "key-1", "trust_root_reference": "trust-root:external", "identity_claims": claims, "signature": "AA=="}
    authority = TestReplayAuthority(ReplayDecision(True, True, True, "authority", "", AuthorityAttestation("authority", True, True, "config:external", "auth:external")))
    retriever = TestEvidenceRetriever(EvidenceBytes(reference, b"evidence", True, True, "custodian:external"))
    return request, response, authority, retriever, claims


def test_protocol_response_controls_block_forgery_key_and_trust_root(monkeypatch):
    import deployment.staging.scripts.verify_gate4_release_manifest as module
    request, response, authority, retriever, claims = _protocol_response_case()
    monkeypatch.setattr(module, "_ed25519_verify", lambda *args: False)
    with pytest.raises(ManifestError, match="signature_invalid"):
        module.verify_authenticated_response(response, request, trust_root={"reference": "trust-root:external", "digest": DIGEST("a"), "version": "v1", "status": "ACTIVE", "keys": {"key-1": "AA=="}}, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(), transparency_authority=TestTransparencyAuthority(), identity_authority=TestIdentityAuthority(claims), expected_provider_identity="provider", now=datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc))
    monkeypatch.setattr(module, "_ed25519_verify", lambda *args: True)
    with pytest.raises(ManifestError, match="key_unknown"):
        module.verify_authenticated_response({**response, "signing_key_id": "unknown"}, request, trust_root={"reference": "trust-root:external", "digest": DIGEST("a"), "version": "v1", "status": "ACTIVE", "keys": {}}, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(), transparency_authority=TestTransparencyAuthority(), identity_authority=TestIdentityAuthority(claims), expected_provider_identity="provider", now=datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc))
    with pytest.raises(ManifestError, match="provider_or_trust_root_mismatch"):
        module.verify_authenticated_response({**response, "trust_root_reference": "wrong"}, request, trust_root={"reference": "trust-root:external", "digest": DIGEST("a"), "version": "v1", "status": "ACTIVE", "keys": {"key-1": "AA=="}}, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(), transparency_authority=TestTransparencyAuthority(), identity_authority=TestIdentityAuthority(claims), expected_provider_identity="provider", now=datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc))


def test_signature_covers_algorithm_and_key_selection_metadata(monkeypatch):
    import deployment.staging.scripts.verify_gate4_release_manifest as module
    request, response, authority, retriever, claims = _protocol_response_case(); captured = []
    monkeypatch.setattr(module, "_ed25519_verify", lambda public, signature, message: captured.append(message) or False)
    trust = {"reference": "trust-root:external", "digest": DIGEST("a"), "version": "v1", "status": "ACTIVE", "keys": {"key-1": "AA==", "key-2": "AA=="}}
    for changed in (response, {**response, "signing_key_id": "key-2"}):
        with pytest.raises(ManifestError, match="signature_invalid"):
            module.verify_authenticated_response(changed, request, trust_root=trust, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(), transparency_authority=TestTransparencyAuthority(), identity_authority=TestIdentityAuthority(claims), expected_provider_identity="provider", now=datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc))
    assert captured[0] != captured[1]


@pytest.mark.parametrize("field", ["nonce", "request_hash", "subject_digest", "candidate", "provider_identity"])
def test_protocol_binding_mismatches_block(monkeypatch, field):
    import deployment.staging.scripts.verify_gate4_release_manifest as module
    request, response, authority, retriever, claims = _protocol_response_case()
    monkeypatch.setattr(module, "_ed25519_verify", lambda *args: True)
    changed = dict(response)
    changed[field] = (b"x" * 32 if field == "nonce" else DIGEST("9") if field in {"request_hash", "subject_digest"} else _protocol_candidate() | {"commit_sha": "c" * 40} if field == "candidate" else "other-provider")
    with pytest.raises(ManifestError):
        module.verify_authenticated_response(changed, request, trust_root={"reference": "trust-root:external", "digest": DIGEST("a"), "version": "v1", "status": "ACTIVE", "keys": {"key-1": "AA=="}}, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(), transparency_authority=TestTransparencyAuthority(), identity_authority=TestIdentityAuthority(claims), expected_provider_identity="provider")


def test_stale_expired_revoked_transparency_identity_and_evidence_fail_closed(monkeypatch):
    import deployment.staging.scripts.verify_gate4_release_manifest as module
    request, response, authority, retriever, claims = _protocol_response_case(); monkeypatch.setattr(module, "_ed25519_verify", lambda *args: True)
    trust = {"reference": "trust-root:external", "digest": DIGEST("a"), "version": "v1", "status": "ACTIVE", "keys": {"key-1": "AA=="}}
    for changed, expected in [({"expires_at": "2026-09-06T00:00:00Z"}, "stale_or_expired"), ({"revocation_status": "REVOKED"}, "trust_evidence_missing"), ({"transparency_reference": ""}, "trust_evidence_missing"), ({"identity_claims": claims | {"approver": claims["requester"]}}, "identity:separation_violation"), ({"evidence_digest": DIGEST("9")}, "evidence:reference_digest_mismatch")]:
        with pytest.raises(ManifestError, match=expected):
            module.verify_authenticated_response({**response, **changed}, request, trust_root=trust, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(False if changed.get("revocation_status") else True), transparency_authority=TestTransparencyAuthority(False if changed.get("transparency_reference") == "" else True), identity_authority=TestIdentityAuthority(changed.get("identity_claims", claims)), expected_provider_identity="provider", now=datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc), replay_already_consumed=True)


def test_incomplete_candidate_and_local_production_dependencies_block():
    with pytest.raises(ManifestError, match="candidate:tuple_incomplete"):
        build_gate4_request(operation="EvidenceVerifier.verify", subject_digest=DIGEST("a"), candidate={"commit_sha": COMMIT})
    with pytest.raises(ManifestError, match="external_authentication_required"):
        verify_independent_evidence({"evidence_reference": "evidence://local/fixture", "evidence_digest": DIGEST("a")}, type("LocalRetriever", (), {"retrieve": lambda self, reference: EvidenceBytes(reference, b"x", True, True, "local")})())
    with pytest.raises(ManifestError, match="production_dependency_injection_forbidden"):
        ExternalSignatureValidator({}, Path("."), replay_authority=TestReplayAuthority(ReplayDecision(True, True, True, "authority", "", AuthorityAttestation("authority", True, True, "config:external", "auth:external"))))


def test_local_production_evidence_retriever_injection_blocks():
    with pytest.raises(ManifestError, match="production_dependency_injection_forbidden"):
        ExternalSignatureValidator({}, Path("."), evidence_retriever=TestEvidenceRetriever(EvidenceBytes("evidence://local/fixture", b"x", True, True, "local")))


def test_independent_revocation_and_transparency_failures_block(monkeypatch):
    import deployment.staging.scripts.verify_gate4_release_manifest as module
    request, response, authority, retriever, claims = _protocol_response_case(); monkeypatch.setattr(module, "_ed25519_verify", lambda *args: True)
    trust = {"reference": "trust-root:external", "digest": DIGEST("a"), "version": "v1", "status": "ACTIVE", "keys": {"key-1": "AA=="}}
    with pytest.raises(ManifestError, match="revocation:independent_verification_failed"):
        module.verify_authenticated_response(response, request, trust_root=trust, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(False), transparency_authority=TestTransparencyAuthority(), identity_authority=TestIdentityAuthority(claims), expected_provider_identity="provider", now=datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc), replay_already_consumed=True)
    with pytest.raises(ManifestError, match="transparency:independent_verification_failed"):
        module.verify_authenticated_response(response, request, trust_root=trust, replay_authority=authority, evidence_retriever=retriever, revocation_authority=TestRevocationAuthority(), transparency_authority=TestTransparencyAuthority(False), identity_authority=TestIdentityAuthority(claims), expected_provider_identity="provider", now=datetime(2026, 9, 7, 0, 5, tzinfo=timezone.utc), replay_already_consumed=True)


def test_local_replay_storage_cannot_satisfy_production_authority_contract():
    authority = UnavailableReplayAuthority()
    with pytest.raises(ManifestError, match="replay_authority_unavailable"):
        authority.consume()


def test_replay_authority_requires_authenticated_atomic_decision():
    request = build_gate4_request(operation="EvidenceVerifier.verify", subject_digest=DIGEST("a"), candidate={"commit_sha": COMMIT, "tree_sha": TREE, "sentinel_image_digests": [DIGEST("a")], "external_boundary_image_digests": [DIGEST("b")], "third_party_image_digests": [DIGEST("c")], "runtime_digest": DIGEST("d"), "lockfile_digest": DIGEST("e"), "browser_executable_digest": DIGEST("f"), "browser_base_image_digest": DIGEST("1"), "browserauth_bridge_digest": DIGEST("2"), "activation_manifest_digest": DIGEST("3"), "edge_configuration_digest": DIGEST("4"), "tls_evidence_digest": DIGEST("5"), "custody_package_digest": DIGEST("6"), "release_manifest_digest": DIGEST("7")})
    from deployment.staging.scripts.verify_gate4_release_manifest import _consume_external_replay
    bad = TestReplayAuthority(ReplayDecision(True, False, True, "authority"))
    with pytest.raises(ManifestError, match="unauthenticated_or_non_atomic"):
        _consume_external_replay(bad, request=request, provider_identity="provider", authority_identity="authority")
    denied = TestReplayAuthority(ReplayDecision(False, True, True, "authority", "REQUEST_REPLAYED", AuthorityAttestation("authority", True, True, "config:external", "auth:external")))
    with pytest.raises(ManifestError, match="provider_denial:REQUEST_REPLAYED"):
        _consume_external_replay(denied, request=request, provider_identity="provider", authority_identity="authority")


def test_evidence_requires_authenticated_immutable_bytes_and_matching_digest():
    evidence_digest = "sha256:" + __import__("hashlib").sha256(b"evidence").hexdigest()
    response = {"evidence_reference": "evidence://external/object?digest=" + evidence_digest, "evidence_digest": evidence_digest}
    retriever = TestEvidenceRetriever(EvidenceBytes(response["evidence_reference"], b"evidence", True, True, "external-custodian"))
    assert verify_independent_evidence(response, retriever) == response["evidence_digest"]
    with pytest.raises(ManifestError, match="evidence_retriever_unavailable"):
        verify_independent_evidence(response, UnavailableEvidenceRetriever())
    with pytest.raises(ManifestError, match="digest_mismatch"):
        verify_independent_evidence({**response, "evidence_digest": DIGEST("b")}, retriever)
    with pytest.raises(ManifestError, match="authenticated_immutable"):
        verify_independent_evidence(response, TestEvidenceRetriever(EvidenceBytes(response["evidence_reference"], b"evidence", False, True, "external-custodian")))
