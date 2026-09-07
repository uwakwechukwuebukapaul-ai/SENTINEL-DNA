import json
from pathlib import Path


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