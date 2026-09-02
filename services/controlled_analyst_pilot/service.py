"""Durable application service for the controlled analyst pilot.

The service uses append-only event tables.  Current tenant and review state is
derived from those events, so a correction is represented by a new event and
never by deleting or rewriting pilot evidence.

Trusted-browser custody/provider readiness is intentionally not implemented
here.  A caller that needs that capability must still pass through the
existing external Gate 4/TB_PROVIDER deployment checks.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import importlib
import json
from typing import Any, Callable
from uuid import uuid4

from database.connection import DatabaseConnection, database
from .models import PilotReviewState, PilotTenantState


class ControlledAnalystPilotError(ValueError):
    """Raised when a pilot operation is invalid or not authorized."""


_REVIEW_ACTIONS = {
    "submitted",
    "accepted",
    "rejected",
    "needs_more_evidence",
    "reopened",
    "withdrawn",
}
_DECISIONS = {
    "accepted",
    "rejected",
    "modified",
    "false_positive",
    "escalated",
    "needs_more_evidence",
}
_ACTIVE_TENANT_STATUSES = {"onboarded", "resumed"}
_MANAGER_ROLES = {"admin", "soc_manager"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any, field: str, maximum: int = 256) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ControlledAnalystPilotError(f"{field}_required")
    if len(normalized) > maximum:
        raise ControlledAnalystPilotError(f"{field}_too_long")
    return normalized


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class ControlledAnalystPilotService:
    """Tenant-scoped onboarding, feedback, review, and audit boundary."""

    def __init__(
        self,
        db: DatabaseConnection | None = None,
        *,
        canonical_authority: Any | None = None,
        audit_service: Any | None = None,
        provisioning_service: Any | None = None,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.db = db or database
        self.canonical_authority = canonical_authority
        self.audit_service = audit_service
        self.provisioning_service = provisioning_service
        self.clock = clock
        migration = importlib.import_module(
            "database.migrations.010_controlled_analyst_pilot"
        )
        with self.db.session() as connection:
            migration.upgrade(connection)

    # ------------------------------------------------------------------
    # Tenant onboarding and lifecycle
    # ------------------------------------------------------------------

    def onboard_provisioned_account(
        self,
        *,
        provisioning_id: str,
        manager_tenant_id: str,
        actor_id: str,
        correlation_id: str,
        display_name: str | None = None,
    ) -> PilotTenantState:
        """Register an account created by the existing bounded provisioner.

        The provisioner remains responsible for the account, canonical tenant,
        role, expiry, and activation token.  This method only adds the
        controlled-pilot projection and never activates a browser/runtime.
        """
        provisioning_id = _text(provisioning_id, "provisioning_id")
        manager_tenant_id = _text(manager_tenant_id, "manager_tenant_id")
        actor_id = _text(actor_id, "actor_id")
        correlation_id = _text(correlation_id, "correlation_id")
        if self.provisioning_service is None:
            raise ControlledAnalystPilotError("provisioning_service_required")
        account = self.provisioning_service.get(
            provisioning_id, manager_tenant_id=manager_tenant_id
        )
        if account is None:
            raise ControlledAnalystPilotError("pilot_account_not_found")
        with self.db.session() as connection:
            self._require_manager(manager_tenant_id, actor_id, connection)
            existing = self._tenant_state(account.tenant_id, connection)
            if existing is not None:
                if existing.status in {"onboarded", "resumed"}:
                    return existing
                raise ControlledAnalystPilotError("pilot_tenant_not_onboardable")
            self._require_analyst(account.tenant_id, account.analyst_id, connection)
            now = self.clock().astimezone(timezone.utc).isoformat()
            event_id = self._id("TENANT")
            self._insert_tenant_event(
                connection,
                event_id=event_id,
                tenant_id=account.tenant_id,
                manager_tenant_id=manager_tenant_id,
                action="onboarded",
                display_name=display_name or account.tenant_id,
                expires_at=account.expires_at,
                provisioning_id=provisioning_id,
                analyst_id=account.analyst_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                occurred_at=now,
            )
            membership_event_id = self._id("MEMBER")
            connection.execute(
                """INSERT INTO controlled_pilot_membership_events(
                    event_id,tenant_id,actor_id,role,action,source_event_id,
                    correlation_id,occurred_at
                    ,sequence_number
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    membership_event_id,
                    account.tenant_id,
                    account.analyst_id,
                    "analyst",
                    "added",
                    event_id,
                    correlation_id,
                    now,
                    self._next_sequence(connection, "controlled_pilot_membership_events", "tenant_id", account.tenant_id),
                ),
            )
            self._record(
                connection,
                tenant_id=account.tenant_id,
                actor_id=actor_id,
                action="pilot_tenant_onboarded",
                resource_type="pilot_tenant",
                resource_id=account.tenant_id,
                correlation_id=correlation_id,
                details={
                    "provisioning_id": provisioning_id,
                    "analyst_id": account.analyst_id,
                    "role": "analyst",
                    "synthetic_only": True,
                    "external_custody_required": True,
                },
            )
            self._audit_legacy(
                "CONTROLLED_PILOT_TENANT_ONBOARDED",
                connection,
                tenant_id=account.tenant_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                resource_type="pilot_tenant",
                resource_id=account.tenant_id,
            )
            return self._tenant_state(account.tenant_id, connection)  # type: ignore[return-value]

    def suspend(
        self, tenant_id: str, *, actor_id: str, correlation_id: str
    ) -> PilotTenantState:
        return self._tenant_transition(
            tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="suspended",
            expected={"onboarded", "resumed"},
        )

    def resume(
        self, tenant_id: str, *, actor_id: str, correlation_id: str
    ) -> PilotTenantState:
        return self._tenant_transition(
            tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="resumed",
            expected={"suspended"},
        )

    def revoke(
        self,
        tenant_id: str,
        *,
        actor_id: str,
        correlation_id: str,
        reason: str,
    ) -> PilotTenantState:
        reason = _text(reason, "reason", 512)
        state = self._tenant_transition(
            tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="revoked",
            expected={"onboarded", "resumed", "suspended"},
            details={"reason": reason},
        )
        # Account/session revocation is delegated to the existing bounded
        # provisioner when available.  Its failure cannot grant access: the
        # append-only pilot state is already terminal and access is denied.
        if self.provisioning_service is not None:
            try:
                self.provisioning_service.revoke(
                    provisioning_id=state.provisioning_id,
                    manager_tenant_id=state.manager_tenant_id,
                    revoked_by=actor_id,
                    reason=reason,
                    audit_correlation_id=correlation_id,
                )
            except Exception:
                pass
        return state

    # ------------------------------------------------------------------
    # Feedback capture
    # ------------------------------------------------------------------

    def capture_feedback(
        self,
        *,
        tenant_id: str,
        analyst_id: str,
        case_id: str,
        investigation_id: str,
        payload: Mapping[str, Any],
        correlation_id: str,
    ) -> dict[str, Any]:
        tenant_id = _text(tenant_id, "tenant_id")
        analyst_id = _text(analyst_id, "analyst_id")
        case_id = _text(case_id, "case_id")
        investigation_id = _text(investigation_id, "investigation_id")
        correlation_id = _text(correlation_id, "correlation_id")
        if not isinstance(payload, Mapping):
            raise ControlledAnalystPilotError("feedback_object_required")
        allowed = {"decision", "helpful_rating", "confidence_rating", "estimated_time_saved", "comments", "metadata"}
        if set(payload) - allowed:
            raise ControlledAnalystPilotError("invalid_feedback_fields")
        decision = _text(payload.get("decision"), "decision", 64).lower()
        if decision not in _DECISIONS:
            raise ControlledAnalystPilotError("invalid_feedback_decision")
        helpful = self._rating(payload.get("helpful_rating"), "helpful_rating")
        confidence = self._rating(payload.get("confidence_rating"), "confidence_rating")
        try:
            saved = float(payload.get("estimated_time_saved"))
        except (TypeError, ValueError) as exc:
            raise ControlledAnalystPilotError("invalid_estimated_time_saved") from exc
        if saved < 0 or saved > 7 * 24 * 60:
            raise ControlledAnalystPilotError("invalid_estimated_time_saved")
        comments = _text(payload.get("comments"), "comments", 2000)
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping) or len(metadata) > 20:
            raise ControlledAnalystPilotError("invalid_feedback_metadata")
        metadata = {str(key)[:64]: str(value)[:256] for key, value in metadata.items()}
        with self.db.session() as connection:
            state = self._tenant_state(tenant_id, connection)
            if not self._active_state(state):
                raise ControlledAnalystPilotError("pilot_tenant_inactive")
            self._require_analyst(tenant_id, analyst_id, connection)
            if state.analyst_id != analyst_id:
                raise ControlledAnalystPilotError("pilot_analyst_mismatch")
            now = self.clock().astimezone(timezone.utc).isoformat()
            feedback_id = self._id("FEEDBACK")
            sequence_number = self._next_sequence(
                connection, "controlled_pilot_feedback", "tenant_id", tenant_id
            )
            connection.execute(
                """INSERT INTO controlled_pilot_feedback(
                    feedback_id,tenant_id,analyst_id,case_id,investigation_id,
                    decision,helpful_rating,confidence_rating,estimated_time_saved,
                    comments,metadata_json,correlation_id,occurred_at,sequence_number
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    feedback_id, tenant_id, analyst_id, case_id, investigation_id,
                    decision, helpful, confidence, saved, comments, _json(metadata),
                    correlation_id, now, sequence_number,
                ),
            )
            details = {"feedback_id": feedback_id, "case_id": case_id, "investigation_id": investigation_id, "decision": decision}
            self._record(connection, tenant_id=tenant_id, actor_id=analyst_id, action="feedback_captured", resource_type="feedback", resource_id=feedback_id, correlation_id=correlation_id, details=details)
            self._audit_legacy("CONTROLLED_PILOT_FEEDBACK_CAPTURED", connection, tenant_id=tenant_id, actor_id=analyst_id, correlation_id=correlation_id, resource_type="feedback", resource_id=feedback_id)
            return {
                "feedback_id": feedback_id,
                "tenant_id": tenant_id,
                "analyst_id": analyst_id,
                "case_id": case_id,
                "investigation_id": investigation_id,
                "decision": decision,
                "helpful_rating": helpful,
                "confidence_rating": confidence,
                "estimated_time_saved": saved,
                "comments": comments,
                "metadata": metadata,
                "occurred_at": now,
            }

    def list_feedback(
        self, tenant_id: str, *, analyst_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        tenant_id = _text(tenant_id, "tenant_id")
        limit = max(1, min(int(limit), 500))
        with self.db.session() as connection:
            tenant_ids = self._visible_tenant_ids(tenant_id, connection)
            if not tenant_ids:
                return []
            placeholders = ",".join("?" for _ in tenant_ids)
            query = f"SELECT * FROM controlled_pilot_feedback WHERE tenant_id IN ({placeholders})"
            params: list[Any] = list(tenant_ids)
            if analyst_id:
                query += " AND analyst_id=?"
                params.append(str(analyst_id))
            query += " ORDER BY sequence_number, feedback_id LIMIT ?"
            params.append(limit)
            rows = connection.execute(query, params).fetchall()
        return [self._feedback_row(row) for row in rows]

    # ------------------------------------------------------------------
    # Review workflow
    # ------------------------------------------------------------------

    def submit_review(
        self,
        *,
        tenant_id: str,
        analyst_id: str,
        case_id: str,
        investigation_id: str,
        decision: str,
        comments: str,
        correlation_id: str,
    ) -> PilotReviewState:
        return self._review_event(
            tenant_id=tenant_id,
            analyst_id=analyst_id,
            case_id=case_id,
            investigation_id=investigation_id,
            actor_id=analyst_id,
            action="submitted",
            decision=decision,
            comments=comments,
            correlation_id=correlation_id,
            actor_must_be="analyst",
        )

    def transition_review(
        self,
        review_id: str,
        *,
        actor_id: str,
        decision: str,
        comments: str,
        correlation_id: str,
    ) -> PilotReviewState:
        with self.db.session() as connection:
            prior = self._review_state(review_id, connection)
            if prior is None:
                raise ControlledAnalystPilotError("review_not_found")
            self._require_manager(prior.tenant_id, actor_id, connection)
            if decision not in {"accepted", "rejected", "needs_more_evidence"}:
                raise ControlledAnalystPilotError("invalid_review_transition")
            # Reopening is a compensating event that records the correction;
            # it does not reopen the original review for a second finalization
            # under the same review id.
            if prior.status not in {"pending_review", "needs_more_evidence"}:
                raise ControlledAnalystPilotError("review_not_transitionable")
            action = decision
            return self._insert_review_event(
                connection, prior=prior, actor_id=actor_id, action=action,
                decision=decision, comments=comments, correlation_id=correlation_id,
            )

    def reopen_review(
        self, review_id: str, *, actor_id: str, reason: str, correlation_id: str
    ) -> PilotReviewState:
        with self.db.session() as connection:
            prior = self._review_state(review_id, connection)
            if prior is None:
                raise ControlledAnalystPilotError("review_not_found")
            self._require_manager(prior.tenant_id, actor_id, connection)
            if prior.status not in {"accepted", "rejected", "withdrawn"}:
                raise ControlledAnalystPilotError("review_not_reopenable")
            return self._insert_review_event(
                connection, prior=prior, actor_id=actor_id, action="reopened",
                decision="needs_more_evidence", comments=reason,
                correlation_id=correlation_id,
            )

    def withdraw_review(
        self, review_id: str, *, actor_id: str, reason: str, correlation_id: str
    ) -> PilotReviewState:
        """Add a compensating withdrawal event without deleting the review."""
        with self.db.session() as connection:
            prior = self._review_state(review_id, connection)
            if prior is None:
                raise ControlledAnalystPilotError("review_not_found")
            self._require_manager(prior.tenant_id, actor_id, connection)
            if prior.status == "withdrawn":
                raise ControlledAnalystPilotError("review_already_withdrawn")
            return self._insert_review_event(
                connection, prior=prior, actor_id=actor_id, action="withdrawn",
                decision=prior.decision, comments=reason,
                correlation_id=correlation_id,
            )

    def list_reviews(self, tenant_id: str, *, limit: int = 100) -> list[PilotReviewState]:
        tenant_id = _text(tenant_id, "tenant_id")
        limit = max(1, min(int(limit), 500))
        with self.db.session() as connection:
            tenant_ids = self._visible_tenant_ids(tenant_id, connection)
            if not tenant_ids:
                return []
            placeholders = ",".join("?" for _ in tenant_ids)
            rows = connection.execute(
                f"SELECT DISTINCT review_id FROM controlled_pilot_review_events WHERE tenant_id IN ({placeholders})",
                tenant_ids,
            ).fetchall()
            states = [self._review_state(row["review_id"], connection) for row in rows]
        return sorted((item for item in states if item), key=lambda item: (item.updated_at, item.review_id))[-limit:]

    # ------------------------------------------------------------------
    # Audit and projections
    # ------------------------------------------------------------------

    def list_audit(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        tenant_id = _text(tenant_id, "tenant_id")
        limit = max(1, min(int(limit), 500))
        with self.db.session() as connection:
            tenant_ids = self._visible_tenant_ids(tenant_id, connection)
            if not tenant_ids:
                return []
            placeholders = ",".join("?" for _ in tenant_ids)
            rows = connection.execute(
                f"SELECT * FROM controlled_pilot_audit_events WHERE tenant_id IN ({placeholders}) ORDER BY occurred_at DESC, audit_id DESC LIMIT ?",
                [*tenant_ids, limit],
            ).fetchall()
        return [self._audit_row(row) for row in rows]

    def tenant_state(self, tenant_id: str) -> PilotTenantState | None:
        with self.db.session() as connection:
            return self._tenant_state(tenant_id, connection)

    def _tenant_transition(self, tenant_id, *, actor_id, correlation_id, action, expected, details=None):
        tenant_id = _text(tenant_id, "tenant_id")
        actor_id = _text(actor_id, "actor_id")
        correlation_id = _text(correlation_id, "correlation_id")
        with self.db.session() as connection:
            prior = self._tenant_state(tenant_id, connection)
            if prior is None:
                raise ControlledAnalystPilotError("pilot_tenant_not_found")
            self._require_manager(prior.manager_tenant_id, actor_id, connection)
            if prior.status not in expected:
                raise ControlledAnalystPilotError("invalid_pilot_tenant_transition")
            now = self.clock().astimezone(timezone.utc).isoformat()
            event_id = self._id("TENANT")
            self._insert_tenant_event(connection, event_id=event_id, tenant_id=prior.tenant_id, manager_tenant_id=prior.manager_tenant_id, action=action, display_name=prior.display_name, expires_at=prior.expires_at, provisioning_id=prior.provisioning_id, analyst_id=prior.analyst_id, actor_id=actor_id, correlation_id=correlation_id, occurred_at=now)
            self._record(connection, tenant_id=tenant_id, actor_id=actor_id, action=f"pilot_tenant_{action}", resource_type="pilot_tenant", resource_id=tenant_id, correlation_id=correlation_id, details=details or {})
            self._audit_legacy(f"CONTROLLED_PILOT_TENANT_{action.upper()}", connection, tenant_id=tenant_id, actor_id=actor_id, correlation_id=correlation_id, resource_type="pilot_tenant", resource_id=tenant_id)
            return self._tenant_state(tenant_id, connection)  # type: ignore[return-value]

    def _review_event(self, *, tenant_id, analyst_id, case_id, investigation_id, actor_id, action, decision, comments, correlation_id, actor_must_be):
        tenant_id = _text(tenant_id, "tenant_id")
        analyst_id = _text(analyst_id, "analyst_id")
        case_id = _text(case_id, "case_id")
        investigation_id = _text(investigation_id, "investigation_id")
        decision = _text(decision, "decision", 64).lower()
        comments = _text(comments, "comments", 2000)
        correlation_id = _text(correlation_id, "correlation_id")
        if decision not in _DECISIONS:
            raise ControlledAnalystPilotError("invalid_review_decision")
        with self.db.session() as connection:
            state = self._tenant_state(tenant_id, connection)
            if not self._active_state(state):
                raise ControlledAnalystPilotError("pilot_tenant_inactive")
            if actor_must_be == "analyst":
                self._require_analyst(tenant_id, analyst_id, connection)
                if state.analyst_id != analyst_id:
                    raise ControlledAnalystPilotError("pilot_analyst_mismatch")
            review_id = self._id("REVIEW")
            now = self.clock().astimezone(timezone.utc).isoformat()
            event_id = self._id("REVIEW-EVENT")
            sequence_number = self._next_sequence(
                connection,
                "controlled_pilot_review_events",
                "tenant_id",
                tenant_id,
                second_column="review_id",
                second_value=review_id,
            )
            connection.execute(
                """INSERT INTO controlled_pilot_review_events(
                    event_id,review_id,tenant_id,case_id,investigation_id,analyst_id,
                    actor_id,action,decision,comments,correlation_id,occurred_at,sequence_number
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event_id, review_id, tenant_id, case_id, investigation_id, analyst_id, actor_id, action, decision, comments, correlation_id, now, sequence_number),
            )
            self._record(connection, tenant_id=tenant_id, actor_id=actor_id, action="review_submitted", resource_type="review", resource_id=review_id, correlation_id=correlation_id, details={"case_id": case_id, "investigation_id": investigation_id, "decision": decision})
            self._audit_legacy("CONTROLLED_PILOT_REVIEW_SUBMITTED", connection, tenant_id=tenant_id, actor_id=actor_id, correlation_id=correlation_id, resource_type="review", resource_id=review_id)
            return self._review_state(review_id, connection)  # type: ignore[return-value]

    def _insert_review_event(self, connection, *, prior, actor_id, action, decision, comments, correlation_id):
        if action not in _REVIEW_ACTIONS:
            raise ControlledAnalystPilotError("invalid_review_transition")
        comments = _text(comments, "comments", 2000)
        correlation_id = _text(correlation_id, "correlation_id")
        now = self.clock().astimezone(timezone.utc).isoformat()
        sequence_number = self._next_sequence(
            connection,
            "controlled_pilot_review_events",
            "tenant_id",
            prior.tenant_id,
            second_column="review_id",
            second_value=prior.review_id,
        )
        connection.execute(
            """INSERT INTO controlled_pilot_review_events(
                event_id,review_id,tenant_id,case_id,investigation_id,analyst_id,
                actor_id,action,decision,comments,correlation_id,occurred_at,sequence_number
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self._id("REVIEW-EVENT"), prior.review_id, prior.tenant_id, prior.case_id, prior.investigation_id, prior.analyst_id, actor_id, action, decision, comments, correlation_id, now, sequence_number),
        )
        self._record(connection, tenant_id=prior.tenant_id, actor_id=actor_id, action=f"review_{action}", resource_type="review", resource_id=prior.review_id, correlation_id=correlation_id, details={"decision": decision})
        self._audit_legacy(f"CONTROLLED_PILOT_REVIEW_{action.upper()}", connection, tenant_id=prior.tenant_id, actor_id=actor_id, correlation_id=correlation_id, resource_type="review", resource_id=prior.review_id)
        return self._review_state(prior.review_id, connection)  # type: ignore[return-value]

    def _tenant_state(self, tenant_id: str, connection) -> PilotTenantState | None:
        rows = connection.execute("SELECT * FROM controlled_pilot_tenant_events WHERE tenant_id=? ORDER BY sequence_number, event_id", (str(tenant_id),)).fetchall()
        if not rows:
            return None
        row = rows[-1]
        return PilotTenantState(tenant_id=str(row["tenant_id"]), manager_tenant_id=str(row["manager_tenant_id"]), display_name=str(row["display_name"]), status=str(row["action"]), expires_at=str(row["expires_at"]), provisioned_by=str(rows[0]["actor_id"]), provisioning_id=str(row["provisioning_id"]), analyst_id=str(row["analyst_id"]))

    @staticmethod
    def _visible_tenant_ids(tenant_id: str, connection) -> tuple[str, ...]:
        """Return a tenant plus pilot tenants managed by that tenant.

        Analyst requests pass their own pilot tenant and therefore resolve to
        one tenant. Manager requests pass the manager tenant and resolve to
        the bounded child pilot tenants recorded in the overlay events.
        """
        rows = connection.execute(
            """SELECT DISTINCT tenant_id
               FROM controlled_pilot_tenant_events
               WHERE tenant_id=? OR manager_tenant_id=?
               ORDER BY tenant_id""",
            (tenant_id, tenant_id),
        ).fetchall()
        return tuple(str(row["tenant_id"]) for row in rows)

    def _review_state(self, review_id: str, connection) -> PilotReviewState | None:
        rows = connection.execute("SELECT * FROM controlled_pilot_review_events WHERE review_id=? ORDER BY sequence_number, event_id", (str(review_id),)).fetchall()
        if not rows:
            return None
        row = rows[-1]
        status = {"submitted": "pending_review", "needs_more_evidence": "needs_more_evidence", "reopened": "reopened", "withdrawn": "withdrawn"}.get(str(row["action"]), str(row["action"]))
        return PilotReviewState(review_id=str(row["review_id"]), tenant_id=str(row["tenant_id"]), case_id=str(row["case_id"]), investigation_id=str(row["investigation_id"]), analyst_id=str(row["analyst_id"]), status=status, decision=str(row["decision"]), comments=str(row["comments"]), last_actor_id=str(row["actor_id"]), updated_at=str(row["occurred_at"]))

    def _active_state(self, state: PilotTenantState | None) -> bool:
        if state is None or state.status not in _ACTIVE_TENANT_STATUSES:
            return False
        try:
            expiry = datetime.fromisoformat(state.expires_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        return expiry.tzinfo is not None and expiry > self.clock().astimezone(timezone.utc)

    def _require_manager(self, tenant_id: str, actor_id: str, connection) -> None:
        if self.canonical_authority is None:
            raise ControlledAnalystPilotError("canonical_authority_required")
        try:
            _tenant, identity, membership = self.canonical_authority.resolve(tenant_id, actor_id, connection=connection)
        except Exception as exc:
            raise ControlledAnalystPilotError("manager_tenant_membership_required") from exc
        if identity.status != "active" or membership.status != "active" or str(membership.role).lower() not in _MANAGER_ROLES:
            raise ControlledAnalystPilotError("manager_role_required")

    def _require_analyst(self, tenant_id: str, actor_id: str, connection) -> None:
        if self.canonical_authority is None:
            raise ControlledAnalystPilotError("canonical_authority_required")
        try:
            _tenant, identity, membership = self.canonical_authority.resolve(tenant_id, actor_id, connection=connection)
        except Exception as exc:
            raise ControlledAnalystPilotError("analyst_tenant_membership_required") from exc
        if identity.status != "active" or membership.status != "active" or str(membership.role).lower() != "analyst":
            raise ControlledAnalystPilotError("analyst_role_required")

    @staticmethod
    def _rating(value: Any, field: str) -> int:
        if isinstance(value, bool):
            raise ControlledAnalystPilotError(f"invalid_{field}")
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ControlledAnalystPilotError(f"invalid_{field}") from exc
        if not 1 <= value <= 5:
            raise ControlledAnalystPilotError(f"invalid_{field}")
        return value

    @staticmethod
    def _id(prefix: str) -> str:
        return f"CP-{prefix}-{uuid4().hex}"

    def _insert_tenant_event(self, connection, **values) -> None:
        sequence_number = self._next_sequence(
            connection,
            "controlled_pilot_tenant_events",
            "tenant_id",
            values["tenant_id"],
        )
        connection.execute(
            """INSERT INTO controlled_pilot_tenant_events(
                event_id,tenant_id,manager_tenant_id,action,display_name,expires_at,
                provisioning_id,analyst_id,actor_id,correlation_id,occurred_at,sequence_number
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            tuple(values[name] for name in ("event_id", "tenant_id", "manager_tenant_id", "action", "display_name", "expires_at", "provisioning_id", "analyst_id", "actor_id", "correlation_id", "occurred_at")) + (sequence_number,),
        )

    def _record(self, connection, *, tenant_id, actor_id, action, resource_type, resource_id, correlation_id, details):
        previous = connection.execute("SELECT event_hash FROM controlled_pilot_audit_events WHERE tenant_id=? ORDER BY sequence_number DESC, audit_id DESC LIMIT 1", (tenant_id,)).fetchone()
        previous_hash = previous["event_hash"] if previous else None
        occurred_at = self.clock().astimezone(timezone.utc).isoformat()
        audit_id = self._id("AUDIT")
        sequence_number = self._next_sequence(connection, "controlled_pilot_audit_events", "tenant_id", tenant_id)
        body = {"audit_id": audit_id, "tenant_id": tenant_id, "actor_id": actor_id, "action": action, "resource_type": resource_type, "resource_id": resource_id, "correlation_id": correlation_id, "details": details, "previous_hash": previous_hash, "occurred_at": occurred_at, "sequence_number": sequence_number}
        event_hash = hashlib.sha256(_json(body).encode()).hexdigest()
        connection.execute("""INSERT INTO controlled_pilot_audit_events(audit_id,tenant_id,actor_id,action,resource_type,resource_id,correlation_id,details_json,previous_hash,event_hash,occurred_at,sequence_number) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (audit_id, tenant_id, actor_id, action, resource_type, resource_id, correlation_id, _json(details), previous_hash, event_hash, occurred_at, sequence_number))

    @staticmethod
    def _next_sequence(connection, table: str, column: str, value: str, *, second_column: str | None = None, second_value: str | None = None) -> int:
        # Table/column names are internal constants, never request input.
        where = f"{column}=?"
        params: list[Any] = [value]
        if second_column is not None:
            where += f" AND {second_column}=?"
            params.append(second_value)
        row = connection.execute(f"SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_sequence FROM {table} WHERE {where}", params).fetchone()
        return int(row["next_sequence"] if hasattr(row, "keys") else row[0])

    def _audit_legacy(self, event_type, connection, **kwargs):
        if self.audit_service is not None:
            self.audit_service.record(event_type, operation="controlled_pilot", outcome="success", connection=connection, **kwargs)

    @staticmethod
    def _feedback_row(row) -> dict[str, Any]:
        value = dict(row)
        value["metadata"] = json.loads(value.pop("metadata_json") or "{}")
        return value

    @staticmethod
    def _audit_row(row) -> dict[str, Any]:
        value = dict(row)
        value["details"] = json.loads(value.pop("details_json") or "{}")
        return value


__all__ = ["ControlledAnalystPilotError", "ControlledAnalystPilotService"]
