"""Operator-controlled onboarding for a FAVP participant.

All identity, organization, contact, and expiry values are mandatory inputs
from the approved operator for a real participant. An explicit ``--synthetic``
mode is also available for disposable staging: it uses a reserved synthetic
identity set, and leaves the linked participant and execution profile in
``INVITED`` until a separate activation command receives explicit operator
confirmation. Neither mode stores credentials.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import database_for_environment  # noqa: E402
from services.audit.service import AuditService  # noqa: E402
from services.favp_operations import FAVPOperationsRepository, FAVPOperationsService, FAVPExecutionService  # noqa: E402


SYNTHETIC_TENANT_ID = "sentinel-dna-staging"
SYNTHETIC_ACTOR_REF = "favp-synthetic-onboarding-operator"
SYNTHETIC_ACTOR_IDENTITY_REF = "favp-synthetic-actor-001"
SYNTHETIC_ORGANIZATION_REF = "favp-synthetic-organization-001"
SYNTHETIC_ORGANIZATION_NAME = "FAVP Synthetic Organization 001"
SYNTHETIC_PARTICIPANT_REF = "favp-synthetic-participant-001"
SYNTHETIC_PARTICIPANT_NAME = "FAVP Synthetic Participant 001"
SYNTHETIC_INVITATION_REF = "synthetic-invitation-001"
SYNTHETIC_CONTACT_REFERENCE = "synthetic-contact-reference-001"


def _synthetic_recovery_invitation_ref(participant_id: str) -> str:
    """Return a stable replacement ref without rewriting the colliding row."""
    return f"{SYNTHETIC_INVITATION_REF}-recovery-{participant_id}"


def _required(value: str, name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise RuntimeError(f"{name} is required")
    return result


def _assert_staging_environment() -> None:
    if os.getenv("SENTINEL_DNA_ENV", "").strip().lower() != "staging":
        raise RuntimeError("participant onboarding requires SENTINEL_DNA_ENV=staging")
    if os.getenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED") != "1":
        raise RuntimeError("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED must be 1")
    if os.getenv("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY") != "1":
        raise RuntimeError("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY must be 1")
    if os.getenv("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0") != "0":
        raise RuntimeError("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS must be 0")
    if os.getenv("SENTINEL_DNA_AUDIT_LOGGING_ENABLED") != "1":
        raise RuntimeError("SENTINEL_DNA_AUDIT_LOGGING_ENABLED must be 1")
    if os.getenv("SENTINEL_DNA_TENANT_ISOLATION_ENABLED") != "1":
        raise RuntimeError("SENTINEL_DNA_TENANT_ISOLATION_ENABLED must be 1")


def _services():
    backend = database_for_environment(require_postgresql=True)
    audit = AuditService(backend)
    operations = FAVPOperationsService(FAVPOperationsRepository(backend), audit)
    return backend, audit, operations, FAVPExecutionService(operations, audit)


def _existing_audit_event(backend, *, tenant_id: str, event_type: str, resource_id: str) -> bool:
    with backend.session() as connection:
        row = connection.execute(
            "SELECT 1 FROM audit_events WHERE tenant_id=? AND event_type=? AND resource_id=? LIMIT 1",
            (tenant_id, event_type, resource_id),
        ).fetchone()
    return bool(row)


def _resolve_or_create_organization(
    operations,
    *,
    tenant_id: str,
    actor_ref: str,
    organization_ref: str,
    display_name: str,
    sector: str | None,
    size_band: str | None,
    create: bool,
):
    existing = operations.repository.get_organization_by_ref(tenant_id, organization_ref)
    if existing:
        return existing
    if not create:
        raise RuntimeError("use an existing --organization-id or explicitly pass --create-organization")
    try:
        return operations.create_organization(
            tenant_id=tenant_id,
            organization_ref=organization_ref,
            display_name=display_name,
            actor_ref=actor_ref,
            sector=sector,
            size_band=size_band,
        )
    except Exception:
        # Recovery may race another operator. If that operation committed the
        # same reserved row, reuse it; never overwrite or delete either row.
        existing = operations.repository.get_organization_by_ref(tenant_id, organization_ref)
        if existing:
            return existing
        raise


def _resolve_or_create_participant(
    operations,
    *,
    tenant_id: str,
    organization_id: str,
    participant_ref: str,
    display_name: str,
    actor_identity_ref: str | None,
    actor_ref: str,
    role_title: str | None,
    contact_reference: str | None,
):
    existing = operations.repository.get_participant_by_ref(tenant_id, participant_ref)
    if existing:
        if existing["organization_id"] != organization_id:
            raise RuntimeError("participant is not owned by the supplied organization")
        return existing
    try:
        return operations.create_participant(
            tenant_id=tenant_id,
            organization_id=organization_id,
            participant_ref=participant_ref,
            display_name=display_name,
            actor_identity_ref=actor_identity_ref,
            actor_ref=actor_ref,
            role_title=role_title,
            contact_reference=contact_reference,
        )
    except Exception:
        existing = operations.repository.get_participant_by_ref(tenant_id, participant_ref)
        if existing:
            if existing["organization_id"] != organization_id:
                raise RuntimeError("participant is not owned by the supplied organization")
            return existing
        raise


def _resolve_or_create_invitation(
    operations,
    *,
    tenant_id: str,
    participant_id: str,
    invitation_ref: str,
    channel: str,
    actor_ref: str,
    sent_at: str | None = None,
    response_at: str | None = None,
):
    # Resolve the complete ownership tuple first. A legacy or stale invitation
    # reference can point at another row, but it must not displace an already-
    # valid invitation belonging to this participant.
    exact = operations.repository.get_invitation_by_participant_and_ref(
        tenant_id, participant_id, invitation_ref
    )
    if exact:
        return exact

    # A previous run may have recorded the same invitation under a legacy ref.
    # Reuse that participant-owned row rather than creating a second lifecycle
    # record. This is especially important for recovery, where invitation rows
    # are append-only and an old ref cannot be rewritten.
    linked_invitations = operations.repository.list_invitation(
        tenant_id, participant_id
    )
    if linked_invitations:
        reusable_linked = next(
            (
                item
                for item in reversed(linked_invitations)
                if item["status"] == "SENT"
            ),
            linked_invitations[-1],
        )
        return reusable_linked

    # Only report a conflict after the participant-scoped lookup has failed.
    # This prevents a stale row using the same ref from being mistaken for the
    # invitation owned by the participant being recovered.
    existing = operations.repository.get_invitation_by_ref(tenant_id, invitation_ref)
    if existing:
        raise RuntimeError("invitation is not owned by the supplied participant")
    try:
        return operations.record_invitation(
            tenant_id=tenant_id,
            participant_id=participant_id,
            invitation_ref=invitation_ref,
            channel=channel,
            status="SENT",
            actor_ref=actor_ref,
            sent_at=sent_at,
            response_at=response_at,
        )
    except Exception:
        exact = operations.repository.get_invitation_by_participant_and_ref(
            tenant_id, participant_id, invitation_ref
        )
        if exact:
            return exact
        linked_invitations = operations.repository.list_invitation(
            tenant_id, participant_id
        )
        if linked_invitations:
            return next(
                (
                    item
                    for item in reversed(linked_invitations)
                    if item["status"] == "SENT"
                ),
                linked_invitations[-1],
            )
        existing = operations.repository.get_invitation_by_ref(tenant_id, invitation_ref)
        if existing:
            raise RuntimeError("invitation is not owned by the supplied participant")
        raise


def _is_reserved_synthetic_participant(item: dict) -> bool:
    return any(
        item.get(field) == expected
        for field, expected in (
            ("actor_identity_ref", SYNTHETIC_ACTOR_IDENTITY_REF),
            ("participant_ref", SYNTHETIC_PARTICIPANT_REF),
            ("display_name", SYNTHETIC_PARTICIPANT_NAME),
            ("contact_reference", SYNTHETIC_CONTACT_REFERENCE),
        )
    )


def _existing_synthetic_participant(
    operations,
    *,
    tenant_id: str,
    participant_id: str | None = None,
    invitation_participant_id: str | None = None,
):
    """Find one reserved synthetic identity deterministically across legacy refs."""
    candidates_by_id = {}
    requested_id = str(participant_id or "").strip()
    if requested_id:
        requested = operations.repository.get_participant(tenant_id, requested_id)
        if requested and not _is_reserved_synthetic_participant(requested):
            raise RuntimeError("participant-id is not a reserved synthetic participant")
        if requested:
            candidates_by_id[requested["participant_id"]] = requested

    candidates = [item for item in operations.repository.list_participants(tenant_id)
                  if _is_reserved_synthetic_participant(item)]
    for item in candidates:
        candidates_by_id[item["participant_id"]] = item

    invitation_id = str(invitation_participant_id or "").strip()
    if invitation_id:
        invitation_participant = operations.repository.get_participant(
            tenant_id, invitation_id
        )
        if invitation_participant and _is_reserved_synthetic_participant(
            invitation_participant
        ):
            candidates_by_id[invitation_participant["participant_id"]] = (
                invitation_participant
            )

    candidates = list(candidates_by_id.values())
    if len(candidates) > 1:
        raise RuntimeError("multiple reserved synthetic participants require review")
    return candidates[0] if candidates else None


def onboard_synthetic(args: argparse.Namespace) -> dict:
    """Create one reserved synthetic staging invitation without activating it.

    The synthetic identifiers are intentionally fixed and visibly marked. All
    required identity fields still flow through the normal required-field
    validation, and all writes use the normal audited service methods.
    """
    _assert_staging_environment()
    if not args.operator_confirmation:
        raise RuntimeError("--operator-confirmation must be supplied for synthetic staging onboarding")

    expiry_days = int(getattr(args, "synthetic_access_days", 30))
    if expiry_days < 1 or expiry_days > 365:
        raise RuntimeError("synthetic-access-days must be between 1 and 365")
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    expiry = (now + timedelta(days=expiry_days)).isoformat()

    tenant_id = _required(SYNTHETIC_TENANT_ID, "tenant-id")
    actor_ref = _required(SYNTHETIC_ACTOR_REF, "actor-ref")
    actor_identity_ref = _required(SYNTHETIC_ACTOR_IDENTITY_REF, "actor-identity-ref")
    organization_ref = _required(SYNTHETIC_ORGANIZATION_REF, "organization-ref")
    organization_name = _required(SYNTHETIC_ORGANIZATION_NAME, "organization-name")
    participant_ref = _required(SYNTHETIC_PARTICIPANT_REF, "participant-ref")
    participant_name = _required(SYNTHETIC_PARTICIPANT_NAME, "participant-name")
    invitation_ref = _required(SYNTHETIC_INVITATION_REF, "invitation-ref")
    contact_reference = _required(SYNTHETIC_CONTACT_REFERENCE, "contact-reference")

    _, audit, operations, execution = _services()
    existing_reserved_invitation = operations.repository.get_invitation_by_ref(
        tenant_id, invitation_ref
    )
    reconciled_participant = None
    if getattr(args, "_allow_invitation_conflict_recovery", False):
        reconciled_participant = _existing_synthetic_participant(
            operations,
            tenant_id=tenant_id,
            participant_id=getattr(args, "participant_id", None),
            invitation_participant_id=(
                existing_reserved_invitation["participant_id"]
                if existing_reserved_invitation
                else None
            ),
        )

    if reconciled_participant:
        organization = operations.repository.get_organization(
            tenant_id, reconciled_participant["organization_id"]
        )
        if not organization:
            raise RuntimeError("reserved synthetic participant organization is missing")
        participant = reconciled_participant
    else:
        organization = _resolve_or_create_organization(
            operations,
            tenant_id=tenant_id,
            organization_ref=organization_ref,
            display_name=organization_name,
            actor_ref=actor_ref,
            sector="synthetic_validation",
            size_band="synthetic_fixture",
            create=True,
        )
        participant = _resolve_or_create_participant(
            operations,
            tenant_id=tenant_id,
            organization_id=organization["organization_id"],
            participant_ref=participant_ref,
            display_name=participant_name,
            actor_identity_ref=actor_identity_ref,
            actor_ref=actor_ref,
            role_title="Synthetic Validation Participant",
            contact_reference=contact_reference,
        )
    invitation_ref_for_recovery = None
    linked_invitations = operations.repository.list_invitation(
        tenant_id, participant["participant_id"]
    )
    reusable_linked_invitation = next(
        (
            item
            for item in reversed(linked_invitations)
            if item["status"] == "SENT"
        ),
        None,
    )
    existing_invitation = operations.repository.get_invitation_by_ref(tenant_id, invitation_ref)
    if (
        existing_invitation
        and existing_invitation["participant_id"] != participant["participant_id"]
    ):
        if not getattr(args, "_allow_invitation_conflict_recovery", False):
            raise RuntimeError("invitation is not owned by the supplied participant")
        # The fixed ref may be left behind by an older/stale participant. A
        # valid invitation already linked to the canonical participant wins;
        # it is safe to reuse and avoids creating a duplicate lifecycle row.
        invitation_ref_for_recovery = (
            reusable_linked_invitation["invitation_ref"]
            if reusable_linked_invitation
            else _synthetic_recovery_invitation_ref(participant["participant_id"])
        )
    elif reusable_linked_invitation and getattr(
        args, "_allow_invitation_conflict_recovery", False
    ):
        # Existing valid synthetic state may use a legacy invitation ref.
        invitation_ref_for_recovery = reusable_linked_invitation["invitation_ref"]
    invitation = _resolve_or_create_invitation(
        operations,
        tenant_id=tenant_id,
        participant_id=participant["participant_id"],
        invitation_ref=invitation_ref_for_recovery or invitation_ref,
        channel="operator_handoff",
        actor_ref=actor_ref,
        sent_at=now_text,
    )
    profile = execution.profile_for_participant(
        tenant_id=tenant_id, participant_id=participant["participant_id"]
    )
    if profile is None:
        try:
            profile = execution.create_profile(
                tenant_id=tenant_id,
                participant_id=participant["participant_id"],
                access_expires_at=expiry,
                actor_ref=actor_ref,
            )
        except Exception:
            # A concurrent recovery can win the profile's tenant/participant
            # uniqueness race. Reuse its committed profile and leave its
            # expiry and lifecycle state untouched.
            profile = execution.profile_for_participant(
                tenant_id=tenant_id, participant_id=participant["participant_id"]
            )
            if profile is None:
                raise
    if not _existing_audit_event(
        operations.repository.db,
        tenant_id=tenant_id,
        event_type="FAVP_SYNTHETIC_INVITATION_CREATED",
        resource_id=participant["participant_id"],
    ):
        audit.record(
            "FAVP_SYNTHETIC_INVITATION_CREATED",
            details={
                "synthetic_only": True,
                "identity_classification": "reserved_synthetic",
                "profile_state": profile["state"],
                "participant_state": participant["state"],
            },
            tenant_id=tenant_id,
            actor_id=actor_ref,
            resource_type="favp_participant",
            resource_id=participant["participant_id"],
            operation="synthetic_onboarding_completed",
            outcome="success",
        )
    return {
        "status": "FAVP_SYNTHETIC_PARTICIPANT_INVITED",
        "synthetic_only": True,
        "tenant_id": tenant_id,
        "organization_id": organization["organization_id"],
        "participant_id": participant["participant_id"],
        "participant_state": participant["state"],
        "invitation_id": invitation["invitation_id"],
        "invitation_ref": invitation["invitation_ref"],
        "invitation_status": invitation["status"],
        "profile_id": profile["profile_id"],
        "profile_state": profile["state"],
        "access_expires_at": profile["access_expires_at"],
        "access_granted": participant["access_status"] == "ACTIVE" and profile["state"] == "ACTIVE",
        "human_program_owner_authorization_required": True,
        "activation_performed": False,
        "credentials_stored": False,
        "audit_recorded": True,
    }


def onboard(args: argparse.Namespace) -> dict:
    _assert_staging_environment()
    if getattr(args, "synthetic", False):
        return onboard_synthetic(args)
    if not args.operator_confirmation:
        raise RuntimeError("--operator-confirmation must be supplied for a real participant")

    tenant_id = _required(args.tenant_id, "tenant-id")
    actor_ref = _required(args.actor_ref, "actor-ref")
    actor_identity_ref = _required(args.actor_identity_ref, "actor-identity-ref")
    participant_ref = _required(args.participant_ref, "participant-ref")
    participant_name = _required(args.participant_name, "participant-name")
    invitation_ref = _required(args.invitation_ref, "invitation-ref")
    expiry = _required(args.access_expires_at, "access-expires-at")
    # Validate before any record is written.
    parsed_expiry = datetime.fromisoformat(expiry[:-1] + "+00:00" if expiry.endswith("Z") else expiry)
    if parsed_expiry.tzinfo is None:
        raise RuntimeError("access-expires-at must include a UTC offset")

    backend, audit, operations, execution = _services()

    if args.organization_id:
        organization = operations.repository.get_organization(tenant_id, _required(args.organization_id, "organization-id"))
        if not organization:
            raise RuntimeError("organization-id is not present in the supplied tenant")
    else:
        organization = _resolve_or_create_organization(
            operations,
            tenant_id=tenant_id,
            organization_ref=_required(args.organization_ref, "organization-ref"),
            display_name=_required(args.organization_name, "organization-name"),
            actor_ref=actor_ref,
            sector=args.sector,
            size_band=args.size_band,
            create=args.create_organization,
        )

    participant = _resolve_or_create_participant(
        operations,
        tenant_id=tenant_id,
        organization_id=organization["organization_id"],
        participant_ref=participant_ref,
        display_name=participant_name,
        actor_identity_ref=actor_identity_ref,
        actor_ref=actor_ref,
        role_title=args.role_title,
        contact_reference=args.contact_reference,
    )
    invitation = _resolve_or_create_invitation(
        operations,
        tenant_id=tenant_id,
        participant_id=participant["participant_id"],
        invitation_ref=invitation_ref,
        channel=_required(args.invitation_channel, "invitation-channel"),
        actor_ref=actor_ref,
    )
    profile = execution.profile_for_participant(
        tenant_id=tenant_id, participant_id=participant["participant_id"]
    )
    if profile is None:
        profile = execution.create_profile(
            tenant_id=tenant_id,
            participant_id=participant["participant_id"],
            access_expires_at=expiry,
            actor_ref=actor_ref,
        )
    return {
        "status": "FAVP_PARTICIPANT_INVITED",
        "organization_id": organization["organization_id"],
        "participant_id": participant["participant_id"],
        "invitation_id": invitation["invitation_id"],
        "profile_id": profile["profile_id"],
        "profile_state": profile["state"],
        "access_granted": False,
        "next_operator_steps": [
            "Record invitation response and verified NDA acceptance.",
            "Record verified terms acceptance and onboarding completion.",
            "Advance the profile through the authorized state transitions only after those checks.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Onboard one operator-supplied FAVP participant")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="complete the reserved synthetic-only staging participant onboarding",
    )
    parser.add_argument("--operator-confirmation", action="store_true")
    parser.add_argument("--synthetic-access-days", type=int, default=30)
    parser.add_argument("--tenant-id")
    parser.add_argument("--actor-ref")
    parser.add_argument("--actor-identity-ref")
    parser.add_argument("--participant-ref")
    parser.add_argument("--participant-name")
    parser.add_argument("--organization-id")
    parser.add_argument("--create-organization", action="store_true")
    parser.add_argument("--organization-ref")
    parser.add_argument("--organization-name")
    parser.add_argument("--sector")
    parser.add_argument("--size-band")
    parser.add_argument("--role-title")
    parser.add_argument("--contact-reference")
    parser.add_argument("--invitation-ref")
    parser.add_argument("--invitation-channel", choices=("operator_handoff", "approved_email_reference", "approved_messaging_reference"))
    parser.add_argument("--access-expires-at")
    args = parser.parse_args()
    print(json.dumps(onboard(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
