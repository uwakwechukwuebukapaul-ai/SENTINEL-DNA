"""Authorization-aware write boundary for canonical decision feedback."""

from __future__ import annotations

from typing import Any, Callable

from .adapters import feedback_from_store_record
from .models import Feedback


class DecisionFeedbackWriteBoundary:
    """Validate decision ownership before delegating to the legacy store."""

    def __init__(
        self,
        decision_source: Any,
        feedback_store: Any,
        tenant_to_organization: Callable[[str], Any],
        authorization: Any,
        audit: Any = None,
    ) -> None:
        if decision_source is None or not hasattr(decision_source, "get"):
            raise ValueError("decision_source_required")
        if feedback_store is None or not hasattr(feedback_store, "record"):
            raise ValueError("feedback_store_required")
        if not callable(tenant_to_organization):
            raise ValueError("tenant_organization_mapping_required")
        if authorization is None or not hasattr(authorization, "require_permission"):
            raise ValueError("tenant_authorization_required")
        self.decision_source = decision_source
        self.feedback_store = feedback_store
        self.tenant_to_organization = tenant_to_organization
        self.authorization = authorization
        self.audit = audit

    def submit(self, context: Any, feedback: Feedback) -> Feedback:
        tenant_id = str(getattr(context, "tenant_id", "") or "").strip()
        actor_id = str(getattr(context, "actor_id", "") or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id_required")
        if not actor_id:
            raise ValueError("actor_id_required")
        if not isinstance(feedback, Feedback):
            raise TypeError("feedback_required")
        if feedback.tenant_id != tenant_id:
            raise ValueError("feedback_tenant_mismatch")
        if feedback.user_id != actor_id:
            raise ValueError("feedback_actor_mismatch")
        if not feedback.decision_id:
            raise ValueError("decision_id_required")

        self.authorization.require_permission(context, tenant_id, "investigations.read")
        decision = self.decision_source.get(tenant_id, feedback.decision_id)
        if decision is None:
            raise ValueError("decision_not_found")
        if str(getattr(decision, "tenant_id", "") or "") != tenant_id:
            raise ValueError("decision_tenant_mismatch")

        organization_id = str(self.tenant_to_organization(tenant_id) or "").strip()
        if not organization_id or organization_id == tenant_id:
            raise ValueError("tenant_organization_mapping_invalid")

        record = self.feedback_store.record(
            organization_id,
            actor_id,
            feedback.decision_id,
            feedback.outcome.value,
            correction=feedback.correction,
            confidence=feedback.confidence,
        )
        normalized = dict(record)
        normalized["tenant_id"] = tenant_id
        normalized["user_id"] = actor_id
        normalized["decision_id"] = feedback.decision_id
        result = feedback_from_store_record(normalized)
        if self.audit is not None and hasattr(self.audit, "record"):
            self.audit.record(
                "DECISION_FEEDBACK_RECORDED",
                user_id=actor_id,
                details={
                    "tenant_id": tenant_id,
                    "organization_id": organization_id,
                    "decision_id": feedback.decision_id,
                    "feedback_id": result.feedback_id,
                    "outcome": result.outcome.value,
                },
            )
        return Feedback(
            feedback_id=result.feedback_id,
            tenant_id=tenant_id,
            user_id=actor_id,
            decision_id=feedback.decision_id,
            outcome=result.outcome,
            correction=result.correction,
            confidence=result.confidence,
            outcome_id=feedback.outcome_id,
            provenance={
                **feedback.provenance,
                "boundary": "decision_feedback_write",
                "decision_tenant_id": tenant_id,
                "actor_id": actor_id,
            },
        )
