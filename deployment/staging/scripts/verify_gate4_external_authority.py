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
import re


REQUIRED_IDENTITY_FIELDS = [
    "organization",
    "human_role",
    "identity_issuer",
    "audience",
    "subject_identifier",
    "authorization_scope",
    "validity",
    "revocation_status",
]
REQUIRED_ROLES = (
    "trust_root_custodian",
    "independent_approver",
    "independent_reviewer",
)
SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
FORBIDDEN_MARKERS = ("example", "test-only", "synthetic", "repository", "local")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_identity(identity: dict):
    errors = []

    if not isinstance(identity, dict):
        return ["identity must be an object"]

    for field in REQUIRED_IDENTITY_FIELDS:
        if not identity.get(field):
            errors.append(
                f"missing identity field: {field}"
            )

    if identity.get("revocation_status") != "ACTIVE":
        errors.append(
            "identity revocation status must be ACTIVE"
        )

    validity = identity.get("validity")
    if not isinstance(validity, dict):
        errors.append("identity validity must be an object")
    else:
        try:
            issued = datetime.fromisoformat(validity["issued_at"].replace("Z", "+00:00"))
            expires = datetime.fromisoformat(validity["expires_at"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if issued.tzinfo is None or expires.tzinfo is None or issued > expires:
                errors.append("identity validity interval is invalid")
            elif expires <= now:
                errors.append("identity metadata is expired")
        except (KeyError, TypeError, ValueError):
            errors.append("identity validity timestamps are invalid")

    for field in ("organization", "identity_issuer", "subject_identifier"):
        value = str(identity.get(field, "")).lower()
        if any(marker in value for marker in FORBIDDEN_MARKERS):
            errors.append(f"identity {field} cannot be repository/test material")

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

    try:
        package = load_json(Path(path))
    except (OSError, json.JSONDecodeError):
        return {"status": "BLOCKED", "errors": ["authority package is unreadable or invalid JSON"]}

    if not isinstance(package, dict) or not package.get("governance_package_id"):
        errors.append("missing governance_package_id")

    for role in REQUIRED_ROLES:
        if role not in package:
            errors.append(
                f"missing authority role: {role}"
            )
            continue

        errors.extend(
            validate_identity(package[role])
        )

    separation = package.get("separation_of_duties")
    if not isinstance(separation, dict) or separation.get("verified") is not True:
        errors.append("separation_of_duties must be externally verified")
    relationships = separation.get("relationships", []) if isinstance(separation, dict) else []
    required_pairs = {
        frozenset(pair) for pair in (
            ("trust_root_custodian", "independent_approver"),
            ("trust_root_custodian", "independent_reviewer"),
            ("independent_approver", "independent_reviewer"),
        )
    }
    observed_pairs = set()
    for relationship in relationships:
        if not isinstance(relationship, dict):
            errors.append("separation relationship must be an object")
            continue
        pair = frozenset((relationship.get("role_a"), relationship.get("role_b")))
        observed_pairs.add(pair)
        if relationship.get("status") != "SATISFIED":
            errors.append("separation relationship is not SATISFIED")
    if not required_pairs.issubset(observed_pairs):
        errors.append("separation_of_duties is missing required role relationships")

    external = package.get("external_verification")
    if not isinstance(external, dict):
        errors.append("missing authenticated external_verification record")
    else:
        if external.get("status") != "VERIFIED":
            errors.append("external_verification is not VERIFIED")
        if not SHA256.fullmatch(str(external.get("evidence_digest", ""))):
            errors.append("external_verification evidence_digest is invalid")
        for field in ("verifier_identity", "evidence_reference", "signature_reference"):
            if not str(external.get(field, "")).strip():
                errors.append(f"external_verification missing {field}")
        try:
            expires = datetime.fromisoformat(external["expires_at"].replace("Z", "+00:00"))
            if expires <= datetime.now(timezone.utc):
                errors.append("external_verification is expired")
        except (KeyError, TypeError, ValueError):
            errors.append("external_verification expiry is invalid")

    if errors:
        return {
            "status": "BLOCKED",
            "errors": errors,
            "external_authority_established": False,
        }

    return {
        "status": "BLOCKED",
        "errors": ["cryptographic authentication and independent governance review must run outside this repository"],
        "external_authority_established": False,
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
