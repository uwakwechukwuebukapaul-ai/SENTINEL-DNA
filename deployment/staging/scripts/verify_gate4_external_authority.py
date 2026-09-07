"""
Gate 4 External Authority Contract Validator

This module validates the structure of externally supplied
authority packages.

It does NOT authenticate external identities,
verify trust roots, approve releases, or create authority.
"""

from pathlib import Path
import json
from datetime import datetime, timezone


REQUIRED_IDENTITY_FIELDS = [
    "organization",
    "human_role",
    "identity_issuer",
    "audience",
    "subject_identifier",
    "authorization_scope",
    "issued_at",
    "expires_at",
    "revocation_status",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_identity(identity: dict):
    errors = []

    for field in REQUIRED_IDENTITY_FIELDS:
        if not identity.get(field):
            errors.append(
                f"missing identity field: {field}"
            )

    if identity.get("revocation_status") not in [
        "ACTIVE",
        "VALID",
        "NOT_REVOKED",
    ]:
        errors.append(
            "identity revocation status invalid"
        )

    return errors


def validate_authority_package(path: str):
    """
    Validate external authority package structure.

    Returns:
        {
            "status": "PASS" | "BLOCKED",
            "errors": []
        }
    """

    errors = []

    package = load_json(Path(path))

    required_roles = [
        "trust_root_custodian",
        "independent_approver",
        "independent_reviewer",
    ]

    for role in required_roles:
        if role not in package:
            errors.append(
                f"missing authority role: {role}"
            )
            continue

        errors.extend(
            validate_identity(package[role])
        )

    if errors:
        return {
            "status": "BLOCKED",
            "errors": errors,
        }

    return {
        "status": "PASS",
        "errors": [],
        "validated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "authority_package",
        help="External authority JSON package",
    )

    args = parser.parse_args()

    result = validate_authority_package(
        args.authority_package
    )

    print(json.dumps(result, indent=2))

    raise SystemExit(
        0 if result["status"] == "PASS" else 1
    )