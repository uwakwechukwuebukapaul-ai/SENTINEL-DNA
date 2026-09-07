import json
from pathlib import Path

from deployment.staging.scripts.verify_gate4_external_authority import (
    validate_authority_package,
)


def test_gate4_missing_authority_blocks(tmp_path):
    package = tmp_path / "authority.json"

    package.write_text(
        "{}",
        encoding="utf-8",
    )

    result = validate_authority_package(
        str(package)
    )

    assert result["status"] == "BLOCKED"
    assert result["errors"]


def test_gate4_repository_only_looking_authority_never_passes(tmp_path):
    package = tmp_path / "authority.json"
    identity = {
        "organization": "Synthetic Test Authority",
        "human_role": "reviewer",
        "identity_issuer": "https://issuer.example.test",
        "audience": "sentinel-dna-gate4",
        "subject_identifier": "test-only-reviewer",
        "authorization_scope": "gate4",
        "validity": {
            "issued_at": "2026-01-01T00:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
        },
        "revocation_status": "ACTIVE",
    }
    package.write_text(json.dumps({
        "governance_package_id": "test-only-package",
        "trust_root_custodian": identity,
        "independent_approver": identity,
        "independent_reviewer": identity,
        "separation_of_duties": {"verified": True, "relationships": []},
        "external_verification": {
            "status": "VERIFIED",
            "evidence_reference": "test-only",
            "evidence_digest": "a" * 64,
            "verifier_identity": "test-only",
            "signature_reference": "test-only",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    }), encoding="utf-8")
    result = validate_authority_package(str(package))
    assert result["status"] == "BLOCKED"
    assert result["external_authority_established"] is False


def test_gate4_expired_identity_blocks(tmp_path):
    package = tmp_path / "authority.json"
    package.write_text(json.dumps({
        "governance_package_id": "pkg",
        "trust_root_custodian": {"validity": {"issued_at": "2020-01-01T00:00:00Z", "expires_at": "2021-01-01T00:00:00Z"}},
        "independent_approver": {},
        "independent_reviewer": {},
    }), encoding="utf-8")
    result = validate_authority_package(str(package))
    assert result["status"] == "BLOCKED"
    assert any("expired" in error for error in result["errors"])

AUTHORITY_SCHEMA = Path(
    "deployment/staging/gate4-authority/GATE4_EXTERNAL_AUTHORITY.schema.json"
)

IDENTITY_SCHEMA = Path(
    "deployment/staging/gate4-authority/GATE4_IDENTITY_ASSIGNMENT.schema.json"
)

VERIFIER_SCHEMA = Path(
    "deployment/staging/gate4-authority/GATE4_EVIDENCE_VERIFIER_RESPONSE.schema.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def test_gate4_external_authority_schema_exists():
    assert AUTHORITY_SCHEMA.exists()


def test_gate4_identity_assignment_schema_exists():
    assert IDENTITY_SCHEMA.exists()


def test_gate4_evidence_verifier_response_schema_exists():
    assert VERIFIER_SCHEMA.exists()


def test_gate4_authority_schema_is_valid_json():
    for schema in [
        AUTHORITY_SCHEMA,
        IDENTITY_SCHEMA,
        VERIFIER_SCHEMA,
    ]:
        data = load_json(schema)
        assert isinstance(data, dict)
        assert "$schema" in data


def test_gate4_authority_contracts_are_repository_only():
    forbidden = [
        "private_key",
        "secret",
        "password",
        "credential",
        "token",
    ]

    for schema in [
        AUTHORITY_SCHEMA,
        IDENTITY_SCHEMA,
        VERIFIER_SCHEMA,
    ]:
        content = schema.read_text(
            encoding="utf-8"
        ).lower()

        for item in forbidden:
            assert item not in content
