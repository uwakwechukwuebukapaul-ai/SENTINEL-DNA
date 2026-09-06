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
    activation_digest = "sha256:" + __import__("hashlib").sha256(Path(ACTIVATION_PATH).read_bytes()).hexdigest()
    return {
        "schema_version": "gate4.release-manifest.v1",
        "release_id": "gate4-test-release",
        "repository": {"owner": "uwakwechukwuebukpaul-ai", "name": "SENTINEL-DNA", "full_name": "uwakwechukwuebukpaul-ai/SENTINEL-DNA", "repository_id": "123456"},
        "commit_sha": COMMIT,
        "tree_sha": TREE,
        "activation_manifest": {"path": ACTIVATION_PATH, "sha256": activation_digest},
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
    lambda value: value["activation_manifest"].update(path="deployment/staging/trusted_browser_activation_manifest.mjs"),
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
    result = authorize_release(
        manifest_path=manifest_path,
        manifest_digest_input=manifest_digest(value),
        signature_path=signature_path,
        repository="uwakwechukwuebukpaul-ai/SENTINEL-DNA",
        head_sha=COMMIT,
        tree_sha=TREE,
        activation_path=Path(ACTIVATION_PATH),
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
    with pytest.raises(ManifestError, match=expected):
        authorize_release(manifest_path=manifest_path, manifest_digest_input=manifest_digest(value), signature_path=signature_path, repository="uwakwechukwuebukpaul-ai/SENTINEL-DNA", head_sha=COMMIT, tree_sha=TREE, activation_path=Path(ACTIVATION_PATH), validator=validator, status_provider=status_provider, trust_policy={"trusted_signer_identity": "release-signer:test", "trusted_issuer": "https://issuer.test", "require_transparency": True}, now=datetime(2026, 9, 6, tzinfo=timezone.utc))


def test_noncanonical_transport_bytes_are_rejected(tmp_path):
    value = valid_manifest()
    path = tmp_path / "release-manifest.json"
    path.write_bytes(canonical_bytes(value) + b"\n")
    with pytest.raises(ManifestError, match="noncanonical_bytes"):
        from deployment.staging.scripts.verify_gate4_release_manifest import load_canonical_manifest
        load_canonical_manifest(path, manifest_digest(value))


@pytest.mark.parametrize("field", ["manifest_digest_input", "head_sha", "tree_sha"])
def test_arbitrary_transport_substitution_is_rejected(tmp_path, field):
    value = valid_manifest()
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_bytes(canonical_bytes(value))
    signature_path = tmp_path / "release-manifest.sig.json"
    _signature(signature_path)
    kwargs = {"manifest_digest_input": manifest_digest(value), "head_sha": COMMIT, "tree_sha": TREE}
    kwargs[field] = "c" * (64 if field == "manifest_digest_input" else 40) if field != "manifest_digest_input" else DIGEST("c")
    with pytest.raises(ManifestError):
        authorize_release(manifest_path=manifest_path, signature_path=signature_path, manifest_digest_input=kwargs["manifest_digest_input"], repository="uwakwechukwuebukpaul-ai/SENTINEL-DNA", head_sha=kwargs["head_sha"], tree_sha=kwargs["tree_sha"], activation_path=Path(ACTIVATION_PATH), validator=GoodSignature(), status_provider=ActiveStatus(), trust_policy={"trusted_signer_identity": "release-signer:test", "trusted_issuer": "https://issuer.test", "require_transparency": True}, now=datetime(2026, 9, 6, tzinfo=timezone.utc))
