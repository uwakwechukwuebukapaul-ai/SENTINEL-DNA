"""Reconcile and activate the reserved synthetic FAVP staging participant.

This is a recoverable operator action for a disposable staging database. It
reuses the reserved organization, participant, invitation, and execution
profile when they exist; missing records are created through the normal
audited onboarding path. Activation remains a separate confirmed operation
and is idempotent after a completed activation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deployment.staging.scripts import activate_favp_participant as activation  # noqa: E402
from deployment.staging.scripts import onboard_favp_participant as onboarding  # noqa: E402


def recover_synthetic(args: argparse.Namespace) -> dict:
    """Reconcile the reserved lifecycle, then run confirmed activation."""
    if not getattr(args, "synthetic", False):
        raise RuntimeError("--synthetic must be supplied for FAVP staging recovery")
    if not getattr(args, "operator_confirmation", False):
        raise RuntimeError("--operator-confirmation must be supplied for FAVP staging recovery")
    requested_tenant = getattr(args, "tenant_id", None)
    if requested_tenant and requested_tenant != onboarding.SYNTHETIC_TENANT_ID:
        raise RuntimeError("synthetic recovery is restricted to the reserved staging tenant")

    activation_args = argparse.Namespace(**vars(args))
    activation_args._allow_invitation_conflict_recovery = True
    reconciled = onboarding.onboard_synthetic(activation_args)
    # Activate the exact invitation selected by reconciliation. This is
    # important when the original reserved ref is occupied by another row;
    # recovery must never reassign or delete that append-only invitation.
    activation_args.tenant_id = reconciled["tenant_id"]
    activation_args.participant_id = reconciled["participant_id"]
    activation_args.profile_id = reconciled["profile_id"]
    activation_args.invitation_id = reconciled["invitation_id"]
    activated = activation.activate_synthetic(activation_args)
    return {
        "status": "FAVP_STAGING_RECOVERED",
        "synthetic_only": True,
        "production_access": "0",
        "human_program_owner_authorization_required": True,
        "activation_performed": False,
        "credentials_stored": False,
        "reconciliation": {
            "tenant_id": reconciled["tenant_id"],
            "organization_id": reconciled["organization_id"],
            "participant_id": reconciled["participant_id"],
            "invitation_id": reconciled["invitation_id"],
            "invitation_ref": reconciled["invitation_ref"],
            "profile_id": reconciled["profile_id"],
            # ``onboard_synthetic`` returns the reconciliation input state.
            # Recovery's externally meaningful state is the result after the
            # confirmed activation step. The invitation row itself remains
            # append-only and therefore retains its physical SENT status.
            "participant_state": activated["participant_state"],
            "profile_state": activated["profile_state"],
            "invitation_status": activated["invitation_status"],
            "invitation_record_status": activated["invitation_record_status"],
        },
        "activation": activated,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover the reserved synthetic FAVP staging lifecycle")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--operator-confirmation", action="store_true")
    parser.add_argument("--tenant-id")
    parser.add_argument("--participant-id")
    parser.add_argument("--profile-id")
    parser.add_argument("--actor-ref")
    args = parser.parse_args()
    print(json.dumps(recover_synthetic(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
