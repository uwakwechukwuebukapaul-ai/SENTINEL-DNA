"""Guarded, out-of-band Gate 1 synthetic identity provisioning.

This service is intentionally not registered as an HTTP route or application
startup hook. It composes the existing authentication, canonical authority,
password hashing, and audit services for one explicitly authorized operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import os
import re
import stat
from pathlib import Path
from typing import Iterable, Mapping

from database.canonical_authority import CanonicalUnitOfWork
from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.phone import normalize_phone
from services.identity.canonical_authority import CanonicalAuthorityService


GATE1_ACTOR = "gate1-synthetic-provisioner"
GATE1_MARKER = "gate1-synthetic"
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TRUSTED_METADATA_RUNTIME_PATH = Path("/run/sentinel/release/metadata.json")


class Gate1ProvisioningError(RuntimeError):
    """Safe operator-facing provisioning failure without sensitive details."""


class Gate1IdentityState:
    ABSENT = "absent"
    ACTIVE_COMPLETE = "active_complete"
    INACTIVE_COMPLETE = "inactive_complete"
    PARTIAL_STATE = "partial_state"
    MIXED_STATE = "mixed_state"
    CONFLICTING_STATE = "conflicting_state"
    UNKNOWN_STATE = "unknown_state"


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


@dataclass(frozen=True)
class RotationState:
    lane: str
    tenant_id: str
    actor_id: str
    user_id: int | None
    state: str


@dataclass(frozen=True)
class RotatedSyntheticIdentity:
    lane: str
    tenant_id: str
    actor_id: str
    user_id: int
    state: str = "rotated"


def _mode_grants_write_to_process(file_stat) -> bool:
    """Return whether POSIX mode bits grant write access to this process."""
    mode = file_stat.st_mode
    if file_stat.st_uid == os.geteuid():
        return bool(mode & stat.S_IWUSR)
    groups = set(os.getgroups()) | {os.getegid()}
    if file_stat.st_gid in groups:
        return bool(mode & stat.S_IWGRP)
    return bool(mode & stat.S_IWOTH)


def _read_only_filesystem(path: Path) -> bool:
    """Require the filesystem containing ``path`` to report read-only."""
    try:
        flags = os.statvfs(path).f_flag
        return bool(flags & getattr(os, "ST_RDONLY", 1))
    except (AttributeError, OSError, ValueError):
        return False


def _metadata_is_effectively_read_only(path: Path) -> bool:
    """Validate effective protection, including Docker Desktop's 9P mounts.

    The application runs in a Linux container. Native Windows execution has no
    portable equivalent for the container mount check and therefore fails
    closed. Docker Desktop may report synthetic POSIX write bits for a Windows
    bind mount even when the mount is read-only; in that case the effective
    access checks and read-only filesystem flag are authoritative.
    """
    if os.name == "nt":
        return False
    try:
        file_stat = os.lstat(path)
        parent_stat = os.lstat(path.parent)
        if not stat.S_ISREG(file_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
            return False
        if os.access(path, os.W_OK) or os.access(path.parent, os.W_OK):
            return False
        if _mode_grants_write_to_process(file_stat) or _mode_grants_write_to_process(parent_stat):
            return _read_only_filesystem(path)
        return True
    except (AttributeError, OSError, ValueError):
        return False


def _read_metadata_from_protected_file(path: Path) -> dict:
    """Open and parse the validated file without following a link."""
    try:
        file_stat = os.lstat(path)
        parent_stat = os.lstat(path.parent)
        if stat.S_ISLNK(file_stat.st_mode) or stat.S_ISLNK(parent_stat.st_mode):
            raise Gate1ProvisioningError("trusted_release_metadata_unavailable")
        if not stat.S_ISREG(file_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
            raise Gate1ProvisioningError("trusted_release_metadata_unavailable")
        if not _metadata_is_effectively_read_only(path):
            raise Gate1ProvisioningError("trusted_release_metadata_writable")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened_stat = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened_stat.st_mode)
                or opened_stat.st_dev != file_stat.st_dev
                or opened_stat.st_ino != file_stat.st_ino
            ):
                raise Gate1ProvisioningError("trusted_release_metadata_unavailable")
            with os.fdopen(descriptor, "r", encoding="utf-8") as metadata_file:
                descriptor = -1
                return json.load(metadata_file)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except Gate1ProvisioningError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError):
        raise Gate1ProvisioningError("trusted_release_metadata_unavailable")


def assert_trusted_release_metadata(expected_revision: str) -> None:
    """Require the deployment-provided, immutable release identity artifact."""
    trusted_path = os.getenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH", "").strip()
    if not trusted_path:
        raise Gate1ProvisioningError("trusted_release_metadata_required")
    path = TRUSTED_METADATA_RUNTIME_PATH
    try:
        configured_path = Path(trusted_path).resolve()
        runtime_path = path.resolve()
    except OSError:
        raise Gate1ProvisioningError("trusted_release_metadata_unavailable")
    if configured_path != runtime_path:
        raise Gate1ProvisioningError("trusted_release_metadata_path_mismatch")
    metadata = _read_metadata_from_protected_file(path)
    if not isinstance(metadata, dict):
        raise Gate1ProvisioningError("trusted_release_metadata_invalid")
    if set(metadata) != {"release_sha", "image_digest"}:
        raise Gate1ProvisioningError("trusted_release_metadata_unexpected_fields")
    trusted_revision = metadata.get("release_sha")
    trusted_digest = metadata.get("image_digest")
    if not isinstance(trusted_revision, str) or not isinstance(trusted_digest, str):
        raise Gate1ProvisioningError("trusted_release_metadata_invalid")
    if not REVISION_PATTERN.fullmatch(trusted_revision) or not IMAGE_DIGEST_PATTERN.fullmatch(trusted_digest):
        raise Gate1ProvisioningError("trusted_release_metadata_invalid")
    if trusted_revision != expected_revision:
        raise Gate1ProvisioningError("trusted_release_revision_mismatch")
    if os.getenv("SENTINEL_DNA_IMAGE_DIGEST", "").strip() != trusted_digest:
        raise Gate1ProvisioningError("image_digest_mismatch")


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
        assert_trusted_release_metadata(self.expected_revision)

    def _assert_rotation_authorized(self) -> None:
        self._assert_authorized()
        if os.getenv("SENTINEL_DNA_GATE1_ROTATION") != "1":
            raise Gate1ProvisioningError("explicit_gate1_rotation_authorization_required")

    @staticmethod
    def _selected_lanes(lanes: Iterable[str]) -> tuple[str, ...]:
        requested = tuple(str(lane).strip().upper() for lane in lanes)
        if not requested or len(set(requested)) != len(requested) or any(lane not in {"A", "B"} for lane in requested):
            raise Gate1ProvisioningError("invalid_gate1_rotation_lane_selection")
        return tuple(spec.lane for spec in synthetic_identity_specs() if spec.lane in requested)

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
        user_by_username = self.auth.get_by_username(spec.username, connection=connection, include_inactive=True)
        user_by_email = self.auth.get_by_email(spec.email, connection=connection, include_inactive=True)
        if user_by_username and user_by_email and user_by_username.id != user_by_email.id:
            raise Gate1ProvisioningError(f"synthetic_identity_conflict_{spec.lane}")
        user = user_by_username or user_by_email
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
            and user.role == "analyst"
            and user.phone_verified_at
            and user.email_verified_at
            and tenant.status == "active"
            and identity.status == "active"
            and membership.status == "active"
            and membership.role == "analyst"
        )

    def _classify(self, spec: SyntheticIdentitySpec, state, connection) -> str:
        user, tenant, identity, membership = state
        if not any(value is not None for value in state):
            orphan = connection.execute(
                "SELECT 1 FROM auth_identities WHERE normalized_identifier=? LIMIT 1",
                (spec.email.lower(),),
            ).fetchone()
            return Gate1IdentityState.CONFLICTING_STATE if orphan else Gate1IdentityState.ABSENT
        if not all(value is not None for value in state):
            return Gate1IdentityState.PARTIAL_STATE
        try:
            self._assert_no_conflict(spec, state)
            if (
                user.role != "analyst"
                or identity.display_name != spec.display_name
                or user.phone_number != spec.phone_number
            ):
                return Gate1IdentityState.CONFLICTING_STATE
            memberships = self.authority.memberships.list_for_actor(spec.actor_id, connection=connection)
            if len(memberships) != 1 or memberships[0] != membership:
                return Gate1IdentityState.CONFLICTING_STATE
            if membership.tenant_id != spec.tenant_id or membership.actor_id != spec.actor_id or membership.role != "analyst":
                return Gate1IdentityState.CONFLICTING_STATE
            identities = self.auth.identities_for_user(user.id, connection=connection)
            if len(identities) != 1:
                return Gate1IdentityState.CONFLICTING_STATE
            password_identity = identities[0]
            if (
                password_identity.get("provider") != "password"
                or str(password_identity.get("provider_subject")) != str(user.id)
                or password_identity.get("normalized_identifier") != spec.email.lower()
            ):
                return Gate1IdentityState.CONFLICTING_STATE
            if not user.email_verified_at or not user.phone_verified_at:
                return Gate1IdentityState.CONFLICTING_STATE
            statuses = ("active" if user.is_active else "inactive", tenant.status, identity.status, membership.status)
            if any(status not in {"active", "inactive"} for status in statuses):
                return Gate1IdentityState.UNKNOWN_STATE
            if all(status == "active" for status in statuses):
                return Gate1IdentityState.ACTIVE_COMPLETE
            if all(status == "inactive" for status in statuses):
                return Gate1IdentityState.INACTIVE_COMPLETE
            return Gate1IdentityState.MIXED_STATE
        except Gate1ProvisioningError:
            return Gate1IdentityState.CONFLICTING_STATE

    def inspect_rotation_state(self, lanes: Iterable[str] = ("A", "B")) -> tuple[RotationState, ...]:
        """Inspect only reserved lanes without exposing authentication material."""
        self._assert_rotation_authorized()
        selected = self._selected_lanes(lanes)
        by_lane = {spec.lane: spec for spec in synthetic_identity_specs()}
        result: list[RotationState] = []
        with CanonicalUnitOfWork(self.db) as unit:
            for lane in selected:
                spec = by_lane[lane]
                try:
                    state = self._state(spec, unit.conn)
                    lifecycle = self._classify(spec, state, unit.conn)
                    user_id = state[0].id if state[0] is not None else None
                except Gate1ProvisioningError:
                    lifecycle = Gate1IdentityState.CONFLICTING_STATE
                    user_id = None
                result.append(RotationState(spec.lane, spec.tenant_id, spec.actor_id, user_id, lifecycle))
        return tuple(result)

    @staticmethod
    def _rotation_state_error(lane: str, state: str) -> Gate1ProvisioningError:
        return Gate1ProvisioningError(f"gate1_rotation_{state}_{lane}")

    def rotate_inactive(
        self,
        replacement_passwords: Mapping[str, str],
        lanes: Iterable[str] = ("A", "B"),
    ) -> tuple[RotatedSyntheticIdentity, ...]:
        """Atomically reactivate only complete, reserved inactive identity graphs."""
        self._assert_rotation_authorized()
        selected = self._selected_lanes(lanes)
        if set(replacement_passwords) != set(selected):
            raise Gate1ProvisioningError("gate1_rotation_password_lane_mismatch")
        specs = tuple(spec for spec in synthetic_identity_specs() if spec.lane in selected)
        results: list[RotatedSyntheticIdentity] = []
        with CanonicalUnitOfWork(self.db) as unit:
            states = {}
            for spec in specs:
                state = self._state(spec, unit.conn)
                lifecycle = self._classify(spec, state, unit.conn)
                if lifecycle != Gate1IdentityState.INACTIVE_COMPLETE:
                    raise self._rotation_state_error(spec.lane, lifecycle)
                states[spec.lane] = state
            for spec in specs:
                password = replacement_passwords[spec.lane]
                if not isinstance(password, str) or len(password) < 10:
                    raise Gate1ProvisioningError(f"synthetic_password_missing_or_too_short_{spec.lane}")
            # Re-read the complete graph inside the same transaction immediately
            # before the first mutation. This closes the role/state TOCTOU
            # window and preserves fail-closed behavior under concurrent review.
            for spec in specs:
                state = self._state(spec, unit.conn)
                lifecycle = self._classify(spec, state, unit.conn)
                if lifecycle != Gate1IdentityState.INACTIVE_COMPLETE:
                    raise self._rotation_state_error(spec.lane, lifecycle)
                states[spec.lane] = state
            for spec in specs:
                user, _tenant, _identity, _membership = states[spec.lane]
                self.auth.reset_password(user.id, replacement_passwords[spec.lane], connection=unit.conn)
                self.authority.memberships.set_status(spec.tenant_id, spec.actor_id, "active", connection=unit.conn)
                self.authority.identities.set_status(spec.actor_id, "active", connection=unit.conn)
                self.authority.tenants.set_status(spec.tenant_id, "active", connection=unit.conn)
                if not self.auth.activate_user(user.id, connection=unit.conn):
                    raise Gate1ProvisioningError(f"gate1_rotation_activation_failed_{spec.lane}")
                self.audit.record(
                    "GATE1_SYNTHETIC_IDENTITY_ROTATED",
                    user_id=user.id,
                    tenant_id=spec.tenant_id,
                    actor_id=GATE1_ACTOR,
                    resource_type="synthetic_identity",
                    resource_id=spec.actor_id,
                    operation="rotate_inactive",
                    outcome="success",
                    metadata={
                        "synthetic": True,
                        "gate": "gate1",
                        "lane": spec.lane,
                        "synthetic_actor_id": spec.actor_id,
                        "previous_lifecycle_state": "inactive_complete",
                        "resulting_lifecycle_state": "active_complete",
                    },
                    connection=unit.conn,
                )
                results.append(RotatedSyntheticIdentity(spec.lane, spec.tenant_id, spec.actor_id, user.id))
        return tuple(results)

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
