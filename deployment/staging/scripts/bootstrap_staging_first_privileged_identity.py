#!/usr/bin/env python3
"""Fail-closed, one-time staging bootstrap for one SOC manager identity."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import getpass
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import database_for_environment
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.privileged_provisioning import (
    PrivilegedIdentityProvisioningService,
    PrivilegedProvisioningError,
    acquire_privileged_tenant_lock,
)
from services.identity.approval_workflow import ApprovalWorkflow, ApprovalWorkflowError
from services.identity.canonical_authority import CanonicalAuthorityService


ROLE = "soc_manager"
PURPOSE = "create_first_staging_control_tenant_soc_manager"
CONFIRMATION = "BOOTSTRAP STAGING FIRST PRIVILEGED IDENTITY"
AUDIT_EVENT = "STAGING_FIRST_PRIVILEGED_IDENTITY_BOOTSTRAPPED"
EXPECTED_DEPLOYMENT_IDENTITY = "sentinel-dna-staging-compose-v1"
EXPECTED_DATABASE_TARGET_IDENTITY = "postgresql://sentinel@postgres:5432/sentinel_dna"
REHEARSAL_DEPLOYMENT_IDENTITY = "sentinel-dna-postgres-rehearsal-v1"


class StagingBootstrapBlocked(RuntimeError):
    """Safe, secret-free operator-facing failure."""


@dataclass(frozen=True)
class BootstrapConfiguration:
    control_tenant_id: str
    database_url: str
    database_target_identity: str


def _require_configuration(environ: dict[str, str] | None = None) -> BootstrapConfiguration:
    values = os.environ if environ is None else environ
    if values.get("SENTINEL_DNA_ENV", "").strip().lower() != "staging":
        raise StagingBootstrapBlocked("staging_environment_required")
    if values.get("SENTINEL_DNA_STAGING_FIRST_ADMIN_BOOTSTRAP") != "1":
        raise StagingBootstrapBlocked("explicit_staging_bootstrap_required")
    deployment_identity = values.get("SENTINEL_DNA_STAGING_DEPLOYMENT_IDENTITY")
    if deployment_identity not in {EXPECTED_DEPLOYMENT_IDENTITY, REHEARSAL_DEPLOYMENT_IDENTITY}:
        raise StagingBootstrapBlocked("approved_staging_deployment_identity_required")
    if values.get("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "").strip().lower() != "disposable_staging":
        raise StagingBootstrapBlocked("disposable_staging_target_required")
    target_identity = values.get("SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY", "").strip()
    database_url = values.get("DATABASE_URL", "").strip()
    derived_target_identity = _database_target_identity(database_url)
    if not target_identity or target_identity != derived_target_identity:
        raise StagingBootstrapBlocked("database_target_identity_mismatch")
    if deployment_identity == EXPECTED_DEPLOYMENT_IDENTITY and target_identity != EXPECTED_DATABASE_TARGET_IDENTITY:
        raise StagingBootstrapBlocked("approved_staging_database_target_required")
    if deployment_identity == REHEARSAL_DEPLOYMENT_IDENTITY and not (
        target_identity.startswith("postgresql://sentinel_rehearsal@127.0.0.1:")
        and target_identity.endswith("/sentinel_dna_rehearsal")
    ):
        raise StagingBootstrapBlocked("approved_staging_database_target_required")
    control_tenant_id = values.get("SENTINEL_DNA_STAGING_CONTROL_TENANT_ID", "").strip()
    if not control_tenant_id:
        raise StagingBootstrapBlocked("staging_control_tenant_required")
    return BootstrapConfiguration(control_tenant_id, database_url, target_identity)


def _database_target_identity(database_url: str) -> str:
    try:
        parsed = urlparse(database_url)
    except ValueError:
        return ""
    try:
        port = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.username
        or parsed.password is not None
        or not parsed.hostname
        or port is None
        or not parsed.path or parsed.path == "/"
        or parsed.query
        or parsed.fragment
    ):
        return ""
    return f"postgresql://{parsed.username}@{parsed.hostname}:{parsed.port}{parsed.path}"


def _validate_connected_target(connection, configuration: BootstrapConfiguration) -> None:
    row = connection.execute(
        "SELECT current_database() AS database_name, current_user AS database_user"
    ).fetchone()
    parsed = urlparse(configuration.database_target_identity)
    if not row or row["database_name"] != parsed.path.lstrip("/") or row["database_user"] != parsed.username:
        raise StagingBootstrapBlocked("database_target_identity_mismatch")


def _check_tenant_and_existing_identity(connection, tenant_id: str) -> None:
    tenant = connection.execute(
        "SELECT status FROM canonical_tenants WHERE tenant_id=?", (tenant_id,)
    ).fetchall()
    if len(tenant) != 1 or tenant[0]["status"] != "active":
        raise StagingBootstrapBlocked("staging_control_tenant_inactive_or_missing")
    existing = connection.execute(
        "SELECT 1 FROM users WHERE tenant_id=? AND is_active=1 "
        "AND role IN ('admin','soc_manager') LIMIT 1", (tenant_id,)
    ).fetchone()
    if existing:
        raise StagingBootstrapBlocked("privileged_identity_exists")
    existing_canonical = connection.execute(
        "SELECT 1 FROM canonical_memberships m "
        "JOIN canonical_identities i ON i.actor_id=m.actor_id "
        "WHERE m.tenant_id=? AND m.status='active' AND i.status='active' "
        "AND m.role IN ('admin','soc_manager') LIMIT 1", (tenant_id,)
    ).fetchone()
    if existing_canonical:
        raise StagingBootstrapBlocked("privileged_identity_exists")


def _artifact(*, tenant_id: str, username: str, email: str, target_identity: str) -> dict[str, str]:
    return {
        "operation": "staging_first_privileged_identity_bootstrap",
        "purpose": PURPOSE,
        "environment": "staging",
        "control_tenant_id": tenant_id,
        "tenant_id": tenant_id,
        "username": username.strip(),
        "email": email.strip().lower(),
        "role": ROLE,
        "database_target_identity": target_identity,
    }


def bootstrap(
    *, db, username: str, email: str, tenant_id: str,
    approval_id: str, approval_transaction_id: str,
    password: str, password_confirmation: str,
    correlation_id: str | None = None,
    services=None, environ: dict[str, str] | None = None,
) -> dict[str, object]:
    """Perform the guarded operation using one caller-owned transaction."""
    configuration = _require_configuration(environ)
    if tenant_id.strip() != configuration.control_tenant_id:
        raise StagingBootstrapBlocked("requested_tenant_is_not_approved_control_tenant")
    if not approval_id.strip() or not approval_transaction_id.strip():
        raise StagingBootstrapBlocked("approval_transaction_required")
    if getattr(db, "backend_name", "") != "postgresql":
        raise StagingBootstrapBlocked("postgresql_database_required")
    correlation = correlation_id or str(uuid4())
    if services is None:
        auth = AuthService(db)
        authority = CanonicalAuthorityService(db)
        audit = AuditService(db)
        service = PrivilegedIdentityProvisioningService(auth, authority, audit, db)
    else:
        auth, authority, audit, service = services
    try:
        with db.session() as connection:
            acquire_privileged_tenant_lock(connection, configuration.control_tenant_id)
            _validate_connected_target(connection, configuration)
            _check_tenant_and_existing_identity(connection, configuration.control_tenant_id)
            approval = ApprovalWorkflow(db).consume_staging_first_privileged_identity_approval(
                connection,
                approval_id=approval_id,
                artifact=_artifact(
                    tenant_id=configuration.control_tenant_id,
                    username=username,
                    email=email,
                    target_identity=configuration.database_target_identity,
                ),
                approval_transaction_id=approval_transaction_id,
                expected_tenant_id=configuration.control_tenant_id,
                expected_database_target_identity=configuration.database_target_identity,
            )
            result = service.provision(
                username=username,
                email=email,
                tenant_id=configuration.control_tenant_id,
                role=ROLE,
                password=password,
                password_confirmation=password_confirmation,
                connection=connection,
                audit_actor_id=approval.approver_actor_id,
            )
            connection.execute(
                """INSERT INTO staging_first_privileged_identity_bootstrap_consumptions(
                    bootstrap_key,tenant_id,approval_id,approval_transaction_id,
                    correlation_id,user_id,created_actor_id,approver_actor_id,
                    approver_user_id,role,outcome,consumed_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "staging-first-privileged-identity-v1",
                    configuration.control_tenant_id,
                    approval.approval_id,
                    approval.approval_transaction_id,
                    correlation,
                    result.user_id,
                    result.actor_id,
                    approval.approver_actor_id,
                    approval.approver_user_id,
                    ROLE,
                    "success",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            audit.record(
                AUDIT_EVENT,
                user_id=result.user_id,
                tenant_id=configuration.control_tenant_id,
                actor_id=approval.approver_actor_id,
                correlation_id=correlation,
                resource_type="user",
                resource_id=str(result.user_id),
                operation="staging_first_privileged_identity_bootstrap",
                outcome="success",
                metadata={
                    "approver_actor_id": approval.approver_actor_id,
                    "approver_user_id": approval.approver_user_id,
                    "created_user_id": result.user_id,
                    "created_actor_id": result.actor_id,
                    "approval_id": approval.approval_id,
                    "approval_transaction_id": approval.approval_transaction_id,
                    "bootstrap_correlation_id": correlation,
                    "approved_tenant_id": configuration.control_tenant_id,
                    "role": ROLE,
                    "outcome": "success",
                },
                connection=connection,
            )
            return {
                "tenant_id": configuration.control_tenant_id,
                "user_id": result.user_id,
                "actor_id": result.actor_id,
                "role": ROLE,
                "approval_id": approval.approval_id,
                "approval_transaction_id": approval.approval_transaction_id,
                "approver_actor_id": approval.approver_actor_id,
                "correlation_id": correlation,
                "outcome": "success",
            }
    except StagingBootstrapBlocked:
        raise
    except ApprovalWorkflowError as exc:
        safe_codes = {
            "approval_not_found", "request_hash_mismatch", "approval_scope_mismatch",
            "approval_not_approved", "approval_transaction_mismatch",
            "approval_already_consumed", "approval_expired",
            "approver_identity_inactive", "requester_reviewer_same_identity",
            "postgresql_required",
        }
        code = str(exc)
        raise StagingBootstrapBlocked(code if code in safe_codes else "approval_invalid") from None
    except PrivilegedProvisioningError as exc:
        safe_codes = {
            "invalid_username", "invalid_email", "invalid_tenant",
            "invalid_privileged_role", "invalid_password",
            "password_confirmation_mismatch", "identity_already_exists",
            "provisioning_failed", "reserved_identity",
        }
        code = str(exc)
        raise StagingBootstrapBlocked(code if code in safe_codes else "provisioning_failed") from None
    except Exception:
        raise StagingBootstrapBlocked("bootstrap_failed") from None
    finally:
        password = ""
        password_confirmation = ""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--approval-transaction-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    first_password = ""
    confirmation = ""
    try:
        _require_configuration()
        if input(f"Type exactly {CONFIRMATION!r} to continue: ") != CONFIRMATION:
            raise StagingBootstrapBlocked("operator_confirmation_required")
        first_password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Confirm password: ")
        db = database_for_environment(require_postgresql=True)
        result = bootstrap(
            db=db,
            username=args.username,
            email=args.email,
            tenant_id=args.tenant_id,
            approval_id=args.approval_id,
            approval_transaction_id=args.approval_transaction_id,
            password=first_password,
            password_confirmation=confirmation,
        )
        print(
            "Staging first privileged identity bootstrapped: "
            f"user_id={result['user_id']}; tenant_id={result['tenant_id']}; role={ROLE}"
        )
        return 0
    except StagingBootstrapBlocked as exc:
        print(f"STAGING BOOTSTRAP BLOCKED: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("STAGING BOOTSTRAP BLOCKED: bootstrap_failed", file=sys.stderr)
        return 1
    finally:
        first_password = ""
        confirmation = ""


if __name__ == "__main__":
    raise SystemExit(main())
