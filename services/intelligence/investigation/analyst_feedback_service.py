"""Canonical append-only analyst feedback application service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .analyst_feedback import AnalystFeedback


class AnalystFeedbackService:
    """Create server-attributed feedback without modifying investigation output.

    The API/coordinator supply the authorized tenant and analyst identity.  The
    request payload supplies only the analyst decision and optional references;
    it cannot select a different tenant, case, investigation, or actor.
    """

    _ALLOWED_FIELDS = frozenset(
        {"decision", "reason", "finding_id", "recommendation_id", "metadata"}
    )

    def __init__(self, repository: Any, audit_service: Any | None = None) -> None:
        self.repository = repository
        self.audit_service = audit_service

    def record(
        self,
        *,
        investigation_id: str,
        case_id: str,
        tenant_id: str,
        analyst_id: str,
        payload: Mapping[str, Any],
        report: Mapping[str, Any] | None = None,
    ) -> AnalystFeedback:
        """Persist one immutable, tenant-scoped analyst outcome event."""
        if not isinstance(payload, Mapping):
            raise ValueError("invalid_feedback_payload")
        if set(payload) - self._ALLOWED_FIELDS:
            raise ValueError("invalid_feedback_fields")

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("invalid_feedback_metadata")

        feedback = AnalystFeedback(
            investigation_id=investigation_id,
            case_id=case_id,
            tenant_id=tenant_id,
            analyst_id=analyst_id,
            decision=payload.get("decision", ""),
            reason=payload.get("reason", ""),
            finding_id=payload.get("finding_id"),
            recommendation_id=payload.get("recommendation_id"),
            metadata=dict(metadata),
        )
        saved = self.repository.save(feedback)
        self._record_audit(saved)
        return saved

    def _record_audit(self, feedback: AnalystFeedback) -> None:
        if self.audit_service is None:
            return
        self.audit_service.record(
            "INVESTIGATION_FEEDBACK_RECORDED",
            case_id=feedback.case_id,
            details={
                "feedback_id": feedback.feedback_id,
                "investigation_id": feedback.investigation_id,
                "tenant_id": feedback.tenant_id,
                "actor_id": feedback.analyst_id,
                "decision": feedback.decision,
            },
        )


__all__ = ["AnalystFeedbackService"]
