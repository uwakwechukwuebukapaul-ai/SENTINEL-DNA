"""Explicitly activate the reserved synthetic FAVP participant in staging.

This command is intentionally separate from invitation creation. It requires
operator confirmation, resolves only the reserved synthetic tenant/participant,
and performs no production migration or production access operation.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import database_for_environment  # noqa: E402
from services.audit.service import AuditService  # noqa: E402
from services.favp_operations import (  # noqa: E402
    FAVPParticipantActivationService,
    FAVPOperationsRepository,
    FAVPOperationsService,
    FAVPExecutionService,
)
from deployment.staging.scripts.onboard_favp_participant import (  # noqa: E402
    SYNTHETIC_ACTOR_REF,
    SYNTHETIC_ACTOR_IDENTITY_REF,
    SYNTHETIC_INVITATION_REF,
    SYNTHETIC_PARTICIPANT_NAME,
    SYNTHETIC_CONTACT_REFERENCE,
    SYNTHETIC_PARTICIPANT_REF,
    SYNTHETIC_TENANT_ID,
)


def _required(value: str, name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise RuntimeError(f"{name} is required")
    return result


def _assert_staging_environment() -> None:
    if os.getenv("SENTINEL_DNA_ENV", "").strip().lower() != "staging":
        raise RuntimeError("participant activation requires SENTINEL_DNA_ENV=staging")
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
    execution = FAVPExecutionService(operations, audit)
    return backend, audit, operations, execution


def activate_synthetic(args: argparse.Namespace) -> dict:
    _assert_staging_environment()
    if not getattr(args, "operator_confirmation", False):
        raise RuntimeError("--operator-confirmation must be supplied for synthetic staging activation")
    if not getattr(args, "synthetic", False):
        raise RuntimeError("--synthetic must be supplied for FAVP activation")

    tenant_id = _required(getattr(args, "tenant_id", None) or SYNTHETIC_TENANT_ID, "tenant-id")
    if tenant_id != SYNTHETIC_TENANT_ID:
        raise RuntimeError("synthetic activation is restricted to the reserved staging tenant")
    actor_ref = _required(getattr(args, "actor_ref", None) or SYNTHETIC_ACTOR_REF, "actor-ref")

    _backend, audit, operations, execution = _services()
    # Bind activation to the invitation selected by onboarding/reconciliation.
    # The normal command uses the reserved ref; recovery may use an additive
    # replacement ref when that append-only ref is already owned elsewhere.
    requested_invitation_id = getattr(args, "invitation_id", None)
    if requested_invitation_id:
        with operations.repository.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM favp_invitations WHERE tenant_id=? AND invitation_id=?",
                (tenant_id, requested_invitation_id),
            ).fetchone()
        invitation = dict(row) if row else None
    else:
        invitation = operations.repository.get_invitation_by_ref(
            tenant_id, SYNTHETIC_INVITATION_REF
        )
    if not invitation:
        raise RuntimeError(
            "synthetic participant invitation was not found; run "
            "onboard_favp_participant.py --synthetic --operator-confirmation "
            "or recover_favp_staging.py --synthetic --operator-confirmation"
        )
    participant = operations.repository.get_participant(tenant_id, invitation["participant_id"])
    if not participant or not (
        participant["participant_ref"] == SYNTHETIC_PARTICIPANT_REF
        or participant["actor_identity_ref"] == SYNTHETIC_ACTOR_IDENTITY_REF
        or participant["display_name"] == SYNTHETIC_PARTICIPANT_NAME
        or participant["contact_reference"] == SYNTHETIC_CONTACT_REFERENCE
    ):
        raise RuntimeError("synthetic invitation is not linked to the reserved participant")
    requested_participant = getattr(args, "participant_id", None)
    if requested_participant and requested_participant != participant["participant_id"]:
        raise RuntimeError("participant-id is not in the reserved synthetic tenant")
    participant_id = participant["participant_id"]

    profile_rows = []
    with operations.repository.db.session() as connection:
        profile_rows = connection.execute(
            "SELECT profile_id FROM favp_execution_profiles WHERE tenant_id=? AND participant_id=?",
            (tenant_id, participant_id),
        ).fetchall()
    if len(profile_rows) != 1:
        raise RuntimeError("synthetic participant must have exactly one execution profile")
    profile_id = profile_rows[0]["profile_id"]
    requested_profile = getattr(args, "profile_id", None)
    if requested_profile and requested_profile != profile_id:
        raise RuntimeError("profile-id is not linked to the reserved synthetic participant")

    activation = FAVPParticipantActivationService(operations, execution, audit)
    return activation.activate(
        tenant_id=tenant_id,
        participant_id=participant_id,
        profile_id=profile_id,
        invitation_id=invitation["invitation_id"],
        actor_ref=actor_ref,
        operator_confirmation=True,
        synthetic_only=True,
    )


def activate(args: argparse.Namespace) -> dict:
    """Compatibility entry point for operators and tests."""
    return activate_synthetic(args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate the reserved synthetic FAVP participant")
    parser.add_argument("--synthetic", action="store_true", help="confirm the reserved synthetic staging participant")
    parser.add_argument("--operator-confirmation", action="store_true", help="confirm the controlled activation")
    parser.add_argument("--tenant-id")
    parser.add_argument("--participant-id")
    parser.add_argument("--profile-id")
    parser.add_argument("--actor-ref")
    args = parser.parse_args()
    print(json.dumps(activate_synthetic(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
