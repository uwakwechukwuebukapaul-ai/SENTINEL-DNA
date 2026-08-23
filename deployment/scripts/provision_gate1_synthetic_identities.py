#!/usr/bin/env python3
"""Provision or expire the two guarded Gate 1 synthetic identities.

This is an operator-only maintenance command. It is not an HTTP endpoint and
is never called by application startup.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.gate1_synthetic_provisioning import (
    Gate1ProvisioningError,
    Gate1SyntheticProvisioningService,
)
from services.identity.canonical_authority import CanonicalAuthorityService


REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _guard(expected_revision: str) -> None:
    """Fail closed before constructing services or opening the database."""
    if os.getenv("SENTINEL_DNA_GATE1_PROVISIONING") != "1":
        raise Gate1ProvisioningError("explicit_gate1_authorization_required")
    if os.getenv("SENTINEL_DNA_ENV") != "production":
        raise Gate1ProvisioningError("production_environment_required")
    if not REVISION_PATTERN.fullmatch(expected_revision):
        raise Gate1ProvisioningError("full_release_revision_required")
    configured_revision = os.getenv("SENTINEL_DNA_IMAGE_REVISION_FULL")
    if configured_revision != expected_revision:
        raise Gate1ProvisioningError("release_revision_mismatch")
    secret_key = os.getenv("SENTINEL_DNA_SECRET_KEY", "").strip()
    if (
        len(secret_key) < 32
        or secret_key.lower() in {"change-me", "replace-with-a-random-secret-before-startup"}
        or "replace-with" in secret_key.lower()
        or "change-me" in secret_key.lower()
    ):
        raise Gate1ProvisioningError("protected_secret_configuration_required")
    db_path = os.getenv("SENTINEL_DNA_DB_PATH", "").strip()
    if not db_path:
        raise Gate1ProvisioningError("database_path_configuration_required")
    if not Path(db_path).is_file():
        raise Gate1ProvisioningError("database_path_unavailable")


def _service() -> Gate1SyntheticProvisioningService:
    db = DatabaseConnection(os.environ["SENTINEL_DNA_DB_PATH"])
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    audit = AuditService(db)
    return Gate1SyntheticProvisioningService(auth, authority, audit, db, expected_revision=os.environ["SENTINEL_DNA_IMAGE_REVISION_FULL"])


def _passwords(service: Gate1SyntheticProvisioningService) -> dict[str, str]:
    passwords: dict[str, str] = {}
    for lane in service.missing_password_lanes():
        first = getpass.getpass(f"Gate 1 synthetic Tenant {lane} password: ")
        second = getpass.getpass(f"Confirm Gate 1 synthetic Tenant {lane} password: ")
        if first != second:
            raise Gate1ProvisioningError(f"synthetic_password_confirmation_failed_{lane}")
        passwords[lane] = first
    return passwords


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision", "cleanup"))
    parser.add_argument("--expected-revision", required=True, help="full immutable Git/image revision")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _guard(args.expected_revision)
        service = _service()
        if args.action == "provision":
            result = service.provision(_passwords(service))
        else:
            result = service.cleanup()
        for item in result:
            print(f"Gate 1 synthetic Tenant {item.lane}: {item.state}; tenant={item.tenant_id}; actor={item.actor_id}; user_id={item.user_id}")
        if not result:
            print("Gate 1 synthetic identities: no active synthetic identities found")
        return 0
    except (Gate1ProvisioningError, ValueError) as exc:
        print(f"Gate 1 synthetic provisioning blocked: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("Gate 1 synthetic provisioning failed: transaction rolled back", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
