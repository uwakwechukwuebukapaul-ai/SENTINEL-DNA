"""Atomic, operator-confirmed activation for the staging FAVP participant."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import FAVP_PROGRAM_STATE_TRANSITIONS
from .execution import EXECUTION_TRANSITIONS


class FAVPActivationError(ValueError):
    """Raised when the controlled activation preconditions are not met."""


_REQUIRED_ACTIVATION_EVENTS = frozenset({
    "FAVP_INVITATION_ACCEPTED",
    "FAVP_NDA_ACCEPTED",
    "FAVP_TERMS_ACCEPTED",
    "FAVP_PARTICIPANT_ACTIVATED",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FAVPParticipantActivationService:
    """Move one invited participant through the two linked FAVP state machines.

    All mutable state changes, timeline entries, and required audit events are
    written in one database transaction. A validation or audit failure rolls
    back the complete activation attempt.
    """

    def __init__(self, operations: Any, execution: Any, audit_service: Any) -> None:
        if operations is None or execution is None or audit_service is None:
            raise FAVPActivationError("activation_dependencies_required")
        if not callable(getattr(audit_service, "record", None)):
            raise FAVPActivationError("audit_service_required")
        self.operations = operations
        self.execution = execution
        self.audit_service = audit_service
        self.db = operations.repository.db

    def _record_audit(self, connection: Any, *, event_type: str, tenant_id: str,
                      actor_ref: str, resource_type: str, resource_id: str,
                      operation: str, details: dict[str, Any] | None = None) -> None:
        self.audit_service.record(
            event_type,
            details=details or {},
            connection=connection,
            tenant_id=tenant_id,
            actor_id=actor_ref,
            resource_type=resource_type,
            resource_id=resource_id,
            operation=operation,
            outcome="success",
        )

    @staticmethod
    def _timeline(connection: Any, *, tenant_id: str, participant_id: str,
                  event_type: str, actor_ref: str, now: str,
                  from_state: str | None = None, to_state: str | None = None,
                  notes: str | None = None) -> None:
        connection.execute(
            """INSERT INTO favp_timeline(
                timeline_id,tenant_id,participant_id,event_type,from_state,
                to_state,actor_ref,notes,occurred_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (f"FAVP-TL-{uuid4().hex}", tenant_id, participant_id, event_type,
             from_state, to_state, actor_ref, notes, now),
        )

    def _has_required_activation_events(
        self,
        connection: Any,
        *,
        tenant_id: str,
        participant_id: str,
        profile_id: str,
        invitation_id: str,
    ) -> bool:
        rows = connection.execute(
            """SELECT DISTINCT event_type FROM audit_events
               WHERE tenant_id=? AND resource_id IN (?,?,?)""",
            (tenant_id, participant_id, profile_id, invitation_id),
        ).fetchall()
        events = {
            row["event_type"] if hasattr(row, "keys") else row[0]
            for row in rows
        }
        return _REQUIRED_ACTIVATION_EVENTS.issubset(events)

    def _result(
        self,
        *,
        tenant_id: str,
        participant_id: str,
        profile_id: str,
        invitation: dict[str, Any],
        idempotent_replay: bool,
    ) -> dict[str, Any]:
        participant = self.operations.repository.get_participant(tenant_id, participant_id)
        profile = self.execution._profile(tenant_id, profile_id)
        return {
            "status": "FAVP_SYNTHETIC_PARTICIPANT_ACTIVATED",
            "tenant_id": tenant_id,
            "participant_id": participant_id,
            "profile_id": profile_id,
            "invitation_id": invitation["invitation_id"],
            "participant_state": participant["state"],
            "profile_state": profile["state"],
            # Invitations are append-only. Acceptance is represented by the
            # immutable audit/timeline transition, while this field reports
            # the resulting lifecycle state.
            "invitation_status": "ACCEPTED",
            "invitation_record_status": invitation["status"],
            "access_granted": True,
            "production_access": "0",
            "synthetic_only": True,
            "human_program_owner_authorization_required": True,
            "activation_performed": False,
            "idempotent_replay": idempotent_replay,
            "audit_events": sorted(_REQUIRED_ACTIVATION_EVENTS),
            "audit_recorded": True,
        }

    def activate(self, *, tenant_id: str, participant_id: str, profile_id: str,
                 invitation_id: str | None = None,
                 actor_ref: str, operator_confirmation: bool = False,
                 synthetic_only: bool = True) -> dict[str, Any]:
        """Explicitly activate one already-invited participant in staging."""
        if not operator_confirmation:
            raise FAVPActivationError("operator_confirmation_required")
        if synthetic_only is not True:
            raise FAVPActivationError("synthetic_only_required")
        tenant_id = str(tenant_id or "").strip()
        participant_id = str(participant_id or "").strip()
        profile_id = str(profile_id or "").strip()
        invitation_id = str(invitation_id or "").strip() or None
        actor_ref = str(actor_ref or "").strip()
        for value, field in ((tenant_id, "tenant_id"), (participant_id, "participant_id"), (profile_id, "profile_id"), (actor_ref, "actor_ref")):
            if not value:
                raise FAVPActivationError(f"{field}_required")

        now = _now()
        with self.db.session() as connection:
            participant = self.operations.repository.get_participant(tenant_id, participant_id, connection=connection)
            if not participant:
                raise FAVPActivationError("participant_not_found")
            profile = self.execution._profile(tenant_id, profile_id, connection=connection)
            if profile["participant_id"] != participant_id:
                raise FAVPActivationError("participant_profile_mismatch")
            if profile["organization_id"] != participant["organization_id"]:
                raise FAVPActivationError("participant_organization_mismatch")

            invitation_query = """SELECT invitation_id,invitation_ref,status FROM favp_invitations
                   WHERE tenant_id=? AND participant_id=?"""
            invitation_params: tuple[Any, ...] = (tenant_id, participant_id)
            if invitation_id:
                invitation_query += " AND invitation_id=?"
                invitation_params += (invitation_id,)
            else:
                invitation_query += " ORDER BY created_at DESC, invitation_id DESC"
            invitation = connection.execute(invitation_query, invitation_params).fetchone()
            if not invitation:
                raise FAVPActivationError("invitation_not_found")
            invitation = dict(invitation)

            fully_active = (
                participant["state"] == "ACTIVE_VALIDATION"
                and participant["access_status"] == "ACTIVE"
                and participant["nda_status"] == "ACCEPTED"
                and participant["terms_status"] == "ACCEPTED"
                and participant["onboarding_status"] == "COMPLETED"
                and profile["state"] == "ACTIVE"
                and profile["nda_status"] == "ACCEPTED"
                and profile["terms_status"] == "ACCEPTED"
                and profile["onboarding_status"] == "COMPLETED"
            )
            if fully_active:
                if invitation["status"] != "SENT":
                    raise FAVPActivationError("invitation_state_invalid_for_replay")
                if not self._has_required_activation_events(
                    connection,
                    tenant_id=tenant_id,
                    participant_id=participant_id,
                    profile_id=profile_id,
                    invitation_id=invitation["invitation_id"],
                ):
                    raise FAVPActivationError("activation_audit_incomplete")
                return self._result(
                    tenant_id=tenant_id,
                    participant_id=participant_id,
                    profile_id=profile_id,
                    invitation=invitation,
                    idempotent_replay=True,
                )

            if participant["state"] != "INVITED":
                raise FAVPActivationError("participant_must_be_invited")
            if profile["state"] != "INVITED":
                raise FAVPActivationError("execution_profile_must_be_invited")
            if participant["access_status"] != "NOT_GRANTED":
                raise FAVPActivationError("participant_access_must_not_be_granted")
            if any(participant[field] != "NOT_STARTED" for field in ("nda_status", "terms_status", "onboarding_status")):
                raise FAVPActivationError("participant_compliance_must_be_unstarted")
            if any(profile[field] != "NOT_STARTED" for field in ("nda_status", "terms_status", "onboarding_status")):
                raise FAVPActivationError("execution_compliance_must_be_unstarted")
            try:
                expiry = datetime.fromisoformat(profile["access_expires_at"].replace("Z", "+00:00"))
            except (TypeError, ValueError) as exc:
                raise FAVPActivationError("access_expires_at_invalid") from exc
            if expiry.tzinfo is None or expiry.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                raise FAVPActivationError("access_expires_at_must_be_future")

            if invitation["status"] != "SENT":
                raise FAVPActivationError("invitation_must_be_pending")

            self._timeline(connection, tenant_id=tenant_id, participant_id=participant_id,
                           event_type="INVITATION_ACCEPTED", actor_ref=actor_ref, now=now,
                           from_state="INVITED", to_state="INVITED",
                           notes="Explicit operator-confirmed synthetic invitation acceptance")
            self._record_audit(connection, event_type="FAVP_INVITATION_ACCEPTED", tenant_id=tenant_id,
                               actor_ref=actor_ref, resource_type="favp_invitation",
                               resource_id=invitation["invitation_id"], operation="invitation_accepted",
                               details={"invitation_ref": invitation["invitation_ref"], "explicit_operator_confirmation": True})

            connection.execute("UPDATE favp_participants SET nda_status='ACCEPTED',updated_at=? WHERE tenant_id=? AND participant_id=?", (now, tenant_id, participant_id))
            self._timeline(connection, tenant_id=tenant_id, participant_id=participant_id,
                           event_type="NDA_ACCEPTED", actor_ref=actor_ref, now=now,
                           notes="Explicit operator-confirmed synthetic NDA acceptance")
            self._record_audit(connection, event_type="FAVP_NDA_ACCEPTED", tenant_id=tenant_id,
                               actor_ref=actor_ref, resource_type="favp_participant", resource_id=participant_id,
                               operation="nda_accepted", details={"explicit_operator_confirmation": True})

            connection.execute("""UPDATE favp_participants SET terms_status='ACCEPTED',
                               onboarding_status='COMPLETED',updated_at=?
                               WHERE tenant_id=? AND participant_id=?""", (now, tenant_id, participant_id))
            self._timeline(connection, tenant_id=tenant_id, participant_id=participant_id,
                           event_type="TERMS_ACCEPTED", actor_ref=actor_ref, now=now,
                           notes="Explicit operator-confirmed synthetic terms acceptance")
            self._record_audit(connection, event_type="FAVP_TERMS_ACCEPTED", tenant_id=tenant_id,
                               actor_ref=actor_ref, resource_type="favp_participant", resource_id=participant_id,
                               operation="terms_accepted", details={"explicit_operator_confirmation": True})
            connection.execute("""UPDATE favp_execution_profiles SET nda_status='ACCEPTED',
                               terms_status='ACCEPTED',onboarding_status='COMPLETED',updated_at=?
                               WHERE tenant_id=? AND profile_id=?""", (now, tenant_id, profile_id))

            current = "INVITED"
            for target in ("APPLIED", "SCREENING", "ACCEPTED", "ONBOARDING", "ACTIVE_VALIDATION"):
                if target not in FAVP_PROGRAM_STATE_TRANSITIONS.get(current, set()):
                    raise FAVPActivationError("invalid_program_state_transition")
                access_status = "ACTIVE" if target == "ACTIVE_VALIDATION" else "NOT_GRANTED"
                phase = "ACTIVE_VALIDATION" if target == "ACTIVE_VALIDATION" else "PROGRAM_SCOPING"
                connection.execute("""UPDATE favp_participants SET state=?,access_status=?,
                                   validation_phase=?,updated_at=? WHERE tenant_id=? AND participant_id=?""", (target, access_status, phase, now, tenant_id, participant_id))
                self._timeline(connection, tenant_id=tenant_id, participant_id=participant_id,
                               event_type="STATE_CHANGED", actor_ref=actor_ref, now=now,
                               from_state=current, to_state=target,
                               notes="Explicit operator-confirmed activation workflow")
                self._record_audit(connection, event_type="FAVP_PARTICIPANT_STATE_CHANGED", tenant_id=tenant_id,
                                   actor_ref=actor_ref, resource_type="favp_participant", resource_id=participant_id,
                                   operation="participant_state_changed", details={"from_state": current, "to_state": target})
                current = target

            profile_current = "INVITED"
            for target in ("APPLIED", "APPROVED", "ONBOARDED", "ACTIVE"):
                if target not in EXECUTION_TRANSITIONS.get(profile_current, set()):
                    raise FAVPActivationError("invalid_execution_state_transition")
                connection.execute("UPDATE favp_execution_profiles SET state=?,updated_at=? WHERE tenant_id=? AND profile_id=?", (target, now, tenant_id, profile_id))
                self._record_audit(connection, event_type="FAVP_EXECUTION_PROFILE_STATE_CHANGED", tenant_id=tenant_id,
                                   actor_ref=actor_ref, resource_type="favp_execution_profile", resource_id=profile_id,
                                   operation="profile_state_changed", details={"from_state": profile_current, "to_state": target})
                profile_current = target

            self._record_audit(connection, event_type="FAVP_PARTICIPANT_ACTIVATED", tenant_id=tenant_id,
                               actor_ref=actor_ref, resource_type="favp_participant", resource_id=participant_id,
                               operation="participant_activated", details={
                                   "participant_state": "ACTIVE_VALIDATION", "profile_state": "ACTIVE",
                                   "synthetic_only": True, "production_access": "0",
                                   "human_program_owner_authorization_required": True,
                                   "activation_performed": False,
                               })

        return self._result(
            tenant_id=tenant_id,
            participant_id=participant_id,
            profile_id=profile_id,
            invitation=dict(invitation),
            idempotent_replay=False,
        )


__all__ = ["FAVPActivationError", "FAVPParticipantActivationService"]
