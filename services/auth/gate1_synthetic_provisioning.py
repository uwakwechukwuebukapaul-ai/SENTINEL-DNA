"""Guarded, out-of-band Gate 1 synthetic identity provisioning.

This service is intentionally not registered as an HTTP route or application
startup hook. It composes the existing authentication, canonical authority,
password hashing, and audit services for one explicitly authorized operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import os
import re
from pathlib import Path
from typing import Mapping

from database.canonical_authority import CanonicalUnitOfWork
from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.phone import normalize_phone
from services.identity.canonical_authority import CanonicalAuthorityService


GATE1_ACTOR = "gate1-synthetic-provisioner"
GATE1_MARKER = "gate1-synthetic"
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class Gate1ProvisioningError(RuntimeError):
    """Safe operator-facing provisioning failure without sensitive details."""


@dataclass(frozen=True)
class SyntheticIdentitySpec:
    lane: str
    tenant_id: str
    tenant_name: str
    actor_id: str
    username: str
    email: str
    display_name: str
    phone_number: str


@dataclass(frozen=True)
class ProvisionedSyntheticIdentity:
    lane: str
    tenant_id: str
    actor_id: str
    user_id: int
    state: str


def synthetic_identity_specs() -> tuple[SyntheticIdentitySpec, ...]:
    """Return the two deterministic, reserved Gate 1 identities."""
    return (
        SyntheticIdentitySpec(
            "A", f"{GATE1_MARKER}-tenant-a", "Gate1 Tenant A",
            f"{GATE1_MARKER}-actor-a", f"{GATE1_MARKER}-user-a",
            "gate1-synthetic-a@synthetic.invalid", "Gate1 Synthetic A",
            normalize_phone("US", "+12025550101"),
        ),
        SyntheticIdentitySpec(
            "B", f"{GATE1_MARKER}-tenant-b", "Gate1 Tenant B",
            f"{GATE1_MARKER}-actor-b", f"{GATE1_MARKER}-user-b",
            "gate1-synthetic-b@synthetic.invalid", "Gate1 Synthetic B",
            normalize_phone("US", "+12025550102"),
        ),
    )


class Gate1SyntheticProvisioningService:
    """Provision or expire only the two explicitly marked Gate 1 identities."""

    def __init__(self, auth: AuthService, authority: CanonicalAuthorityService, audit: AuditService, db: DatabaseConnection, expected_revision: str):
        self.auth = auth
        self.authority = authority
        self.audit = audit
        self.db = db
        self.expected_revision = expected_revision

    def _assert_authorized(self) -> None:
        """Recheck the operator boundary even when called outside the CLI."""
        if os.getenv("SENTINEL_DNA_GATE1_PROVISIONING") != "1":
            raise Gate1ProvisioningError("explicit_gate1_authorization_required")
        if os.getenv("SENTINEL_DNA_ENV") != "production":
            raise Gate1ProvisioningError("production_environment_required")
        if not REVISION_PATTERN.fullmatch(self.expected_revision):
            raise Gate1ProvisioningError("full_release_revision_required")
        if os.getenv("SENTINEL_DNA_IMAGE_REVISION_FULL") != self.expected_revision:
            raise Gate1ProvisioningError("release_revision_mismatch")
        secret_key = os.getenv("SENTINEL_DNA_SECRET_KEY", "").strip()
        if (
            len(secret_key) < 32
            or "replace-with" in secret_key.lower()
            or "change-me" in secret_key.lower()
        ):
            raise Gate1ProvisioningError("protected_secret_configuration_required")
        configured_path = os.getenv("SENTINEL_DNA_DB_PATH", "").strip()
        if not configured_path:
            raise Gate1ProvisioningError("database_path_configuration_required")
        if not Path(configured_path).is_file():
            raise Gate1ProvisioningError("database_path_unavailable")
        if Path(configured_path).resolve() != Path(self.db.database_path).resolve():
            raise Gate1ProvisioningError("database_path_mismatch")

    @staticmethod
    def _user_matches(user, spec: SyntheticIdentitySpec) -> bool:
        return bool(
            user
            and user.username == spec.username
            and user.email == spec.email
            and user.tenant_id == spec.tenant_id
            and user.actor_id == spec.actor_id
        )

    def _state(self, spec: SyntheticIdentitySpec, connection):
        user = self.auth.get_by_username(spec.username, connection=connection)
        if user is None:
            user = self.auth.get_by_email(spec.email, connection=connection, include_inactive=True)
        tenant = self.authority.tenants.get(spec.tenant_id, connection=connection)
        identity = self.authority.identities.get(spec.actor_id, connection=connection)
        membership = self.authority.memberships.get(spec.tenant_id, spec.actor_id, connection=connection)
        return user, tenant, identity, membership

    def _assert_no_conflict(self, spec: SyntheticIdentitySpec, state) -> None:
        user, tenant, identity, membership = state
        if user is not None and not self._user_matches(user, spec):
            raise Gate1ProvisioningError(f"synthetic_identity_conflict_{spec.lane}")
        if tenant is not None and (tenant.tenant_id != spec.tenant_id or tenant.name != spec.tenant_name):
            raise Gate1ProvisioningError(f"synthetic_tenant_conflict_{spec.lane}")
        if identity is not None and (identity.actor_id != spec.actor_id or identity.email != spec.email):
            raise Gate1ProvisioningError(f"synthetic_identity_authority_conflict_{spec.lane}")
        if membership is not None and membership.tenant_id != spec.tenant_id:
            raise Gate1ProvisioningError(f"synthetic_membership_conflict_{spec.lane}")

    @staticmethod
    def _complete(spec: SyntheticIdentitySpec, state) -> bool:
        user, tenant, identity, membership = state
        return bool(
            user
            and tenant
            and identity
            and membership
            and user.is_active
            and user.phone_verified_at
            and user.email_verified_at
            and tenant.status == "active"
            and identity.status == "active"
            and membership.status == "active"
            and membership.role == "analyst"
        )

    def provision(self, passwords: Mapping[str, str]) -> tuple[ProvisionedSyntheticIdentity, ...]:
        self._assert_authorized()
        specs = synthetic_identity_specs()
        results: list[ProvisionedSyntheticIdentity] = []
        with CanonicalUnitOfWork(self.db) as unit:
            states = {spec.lane: self._state(spec, unit.conn) for spec in specs}
            for spec in specs:
                self._assert_no_conflict(spec, states[spec.lane])
            if all(self._complete(spec, states[spec.lane]) for spec in specs):
                for spec in specs:
                    self.audit.record(
                        "GATE1_SYNTHETIC_IDENTITY_REUSED",
                        user_id=states[spec.lane][0].id,
                        tenant_id=spec.tenant_id,
                        actor_id=GATE1_ACTOR,
                        resource_type="synthetic_identity",
                        resource_id=spec.actor_id,
                        operation="provision",
                        outcome="already_exists",
                        metadata={"synthetic": True, "gate": "gate1", "lane": spec.lane, "synthetic_actor_id": spec.actor_id},
                        connection=unit.conn,
                    )
                return tuple(
                    ProvisionedSyntheticIdentity(spec.lane, spec.tenant_id, spec.actor_id, states[spec.lane][0].id, "already_provisioned")
                    for spec in specs
                )
            if any(any(value is not None for value in states[spec.lane]) for spec in specs):
                raise Gate1ProvisioningError("synthetic_identity_partial_state_requires_review")
            if any(len(str(passwords.get(spec.lane, ""))) < 10 for spec in specs):
                raise Gate1ProvisioningError("synthetic_password_missing_or_too_short")

            verified_at = datetime.now(timezone.utc).isoformat()
            dob = date(2000, 1, 1).isoformat()
            for spec in specs:
                tenant = self.authority.tenants.create(spec.tenant_name, spec.tenant_id, connection=unit.conn)
                identity = self.authority.identities.create(spec.email, spec.display_name, spec.actor_id, connection=unit.conn)
                membership = self.authority.memberships.add(spec.tenant_id, spec.actor_id, "analyst", connection=unit.conn)
                user = self.auth.register(
                    spec.username,
                    spec.email,
                    passwords[spec.lane],
                    "analyst",
                    phone_number=spec.phone_number,
                    phone_verified_at=verified_at,
                    tenant_id=spec.tenant_id,
                    actor_id=spec.actor_id,
                    date_of_birth=dob,
                    email_verified_at=verified_at,
                    connection=unit.conn,
                )
                if not (tenant and identity and membership and user):
                    raise Gate1ProvisioningError(f"synthetic_identity_creation_failed_{spec.lane}")
                self.audit.record(
                    "GATE1_SYNTHETIC_IDENTITY_PROVISIONED",
                    user_id=user.id,
                    tenant_id=spec.tenant_id,
                    actor_id=GATE1_ACTOR,
                    resource_type="synthetic_identity",
                    resource_id=spec.actor_id,
                    operation="provision",
                    outcome="success",
                    metadata={"synthetic": True, "gate": "gate1", "lane": spec.lane, "synthetic_actor_id": spec.actor_id},
                    connection=unit.conn,
                )
                results.append(ProvisionedSyntheticIdentity(spec.lane, spec.tenant_id, spec.actor_id, user.id, "provisioned"))
        return tuple(results)

    def missing_password_lanes(self) -> tuple[str, ...]:
        """Return lanes requiring credentials without changing persistence."""
        self._assert_authorized()
        specs = synthetic_identity_specs()
        with CanonicalUnitOfWork(self.db) as unit:
            states = {spec.lane: self._state(spec, unit.conn) for spec in specs}
            for spec in specs:
                self._assert_no_conflict(spec, states[spec.lane])
            if all(self._complete(spec, states[spec.lane]) for spec in specs):
                return ()
            if any(any(value is not None for value in states[spec.lane]) for spec in specs):
                raise Gate1ProvisioningError("synthetic_identity_partial_state_requires_review")
            return tuple(spec.lane for spec in specs)

    def cleanup(self) -> tuple[ProvisionedSyntheticIdentity, ...]:
        self._assert_authorized()
        specs = synthetic_identity_specs()
        results: list[ProvisionedSyntheticIdentity] = []
        with CanonicalUnitOfWork(self.db) as unit:
            states = {spec.lane: self._state(spec, unit.conn) for spec in specs}
            for spec in specs:
                self._assert_no_conflict(spec, states[spec.lane])
                if any(value is not None for value in states[spec.lane]) and not all(value is not None for value in states[spec.lane]):
                    raise Gate1ProvisioningError(f"synthetic_identity_partial_state_requires_review_{spec.lane}")
            for spec in specs:
                user, tenant, identity, membership = states[spec.lane]
                if user is None:
                    continue
                self.auth.deactivate_user(user.id, connection=unit.conn)
                self.authority.memberships.set_status(spec.tenant_id, spec.actor_id, "inactive", connection=unit.conn)
                self.authority.identities.set_status(spec.actor_id, "inactive", connection=unit.conn)
                self.authority.tenants.set_status(spec.tenant_id, "inactive", connection=unit.conn)
                self.audit.record(
                    "GATE1_SYNTHETIC_IDENTITY_CLEANED",
                    user_id=user.id,
                    tenant_id=spec.tenant_id,
                    actor_id=GATE1_ACTOR,
                    resource_type="synthetic_identity",
                    resource_id=spec.actor_id,
                    operation="cleanup",
                    outcome="success",
                    metadata={"synthetic": True, "gate": "gate1", "lane": spec.lane, "synthetic_actor_id": spec.actor_id},
                    connection=unit.conn,
                )
                results.append(ProvisionedSyntheticIdentity(spec.lane, spec.tenant_id, spec.actor_id, user.id, "cleaned"))
        return tuple(results)
