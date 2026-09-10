#!/usr/bin/env python3
"""Provision one tenant-bound admin or SOC manager through an operator CLI."""

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
from services.auth.privileged_provisioning import (
    PRIVILEGED_ROLES,
    PrivilegedIdentityProvisioningService,
    PrivilegedProvisioningError,
)
from services.identity.canonical_authority import CanonicalAuthorityService


REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _guard(expected_revision: str) -> None:
    """Fail closed before constructing services or opening the database."""
    if os.getenv("SENTINEL_DNA_PRIVILEGED_BOOTSTRAP") != "1":
        raise PrivilegedProvisioningError("explicit_privileged_bootstrap_required")
    if os.getenv("SENTINEL_DNA_ENV") != "production":
        raise PrivilegedProvisioningError("production_environment_required")
    if not REVISION_PATTERN.fullmatch(expected_revision):
        raise PrivilegedProvisioningError("full_release_revision_required")
    if os.getenv("SENTINEL_DNA_IMAGE_REVISION_FULL") != expected_revision:
        raise PrivilegedProvisioningError("release_revision_mismatch")
    if os.getenv("SENTINEL_DNA_SECURE_COOKIES") != "1":
        raise PrivilegedProvisioningError("secure_cookies_required")
    secret_key = os.getenv("SENTINEL_DNA_SECRET_KEY", "").strip()
    if (
        len(secret_key) < 32
        or "replace-with" in secret_key.lower()
        or "change-me" in secret_key.lower()
    ):
        raise PrivilegedProvisioningError("protected_secret_configuration_required")
    db_path = os.getenv("SENTINEL_DNA_DB_PATH", "").strip()
    if not db_path:
        raise PrivilegedProvisioningError("database_path_configuration_required")
    if not Path(db_path).is_file():
        raise PrivilegedProvisioningError("database_path_unavailable")


def _service() -> PrivilegedIdentityProvisioningService:
    db = DatabaseConnection(os.environ["SENTINEL_DNA_DB_PATH"])
    return PrivilegedIdentityProvisioningService(
        AuthService(db),
        CanonicalAuthorityService(db),
        AuditService(db),
        db,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--tenant", required=True, dest="tenant_id")
    parser.add_argument("--role", required=True, choices=sorted(PRIVILEGED_ROLES))
    parser.add_argument("--expected-revision", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _guard(args.expected_revision)
        print("You are about to provision:")
        print(f"Username: {args.username}")
        print(f"Email: {args.email}")
        print(f"Tenant: {args.tenant_id}")
        print(f"Role: {args.role}")
        if input("Continue? [y/N]: ").strip().lower() != "y":
            print("Provisioning cancelled.")
            return 1

        first_password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Confirm password: ")
        try:
            result = _service().provision(
                username=args.username,
                email=args.email,
                tenant_id=args.tenant_id,
                role=args.role,
                password=first_password,
                password_confirmation=confirmation,
            )
        finally:
            first_password = ""
            confirmation = ""

        print(
            "Privileged identity provisioned: "
            f"username={result.username}; tenant={result.tenant_id}; "
            f"role={result.role}; user_id={result.user_id}"
        )
        return 0
    except PrivilegedProvisioningError as exc:
        print(f"PROVISIONING BLOCKED: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("PROVISIONING BLOCKED: provisioning_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
