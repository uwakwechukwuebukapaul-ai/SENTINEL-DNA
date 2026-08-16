"""One-way adapters from existing subsystem records to canonical contracts."""

from __future__ import annotations

from typing import Any, Mapping

from .models import Feedback, FeedbackOutcome, LearningSignal, Outcome, OutcomeStatus, QualityAssessment, QualityScope


def outcome_from_record(record: Any) -> Outcome:
    """Adapt outcome_learning.OutcomeRecord without importing that subsystem."""
    status = str(getattr(record, "verification_status", "UNKNOWN")).upper()
    status = OutcomeStatus._value2member_map_.get(status, OutcomeStatus.UNKNOWN)
    return Outcome(
        tenant_id=record.tenant_id,
        lifecycle_id=record.lifecycle_id,
        outcome_id=record.outcome_id,
        status=status,
        case_id=getattr(record, "case_id", ""),
        investigation_id=getattr(record, "investigation_id", ""),
        verification_status=status,
        decision_reference=getattr(record, "decision_reference", ""),
        action_reference=getattr(record, "action_reference", ""),
        evidence_references=tuple(getattr(record, "evidence_references", ()) or ()),
        provenance=getattr(record, "provenance", {}) or {},
    )


def feedback_from_store_record(record: Mapping[str, Any]) -> Feedback:
    """Adapt a FeedbackStore dictionary and normalize organization_id to tenant_id."""
    raw_outcome = str(record.get("outcome", "")).lower()
    outcome = FeedbackOutcome._value2member_map_.get(raw_outcome)
    if outcome is None:
        raise ValueError("unsupported_feedback_outcome")
    return Feedback(
        feedback_id=str(record["id"]),
        tenant_id=str(record.get("tenant_id") or record.get("organization_id") or ""),
        user_id=str(record.get("user_id") or ""),
        decision_id=str(record.get("decision_id") or ""),
        outcome=outcome,
        correction=record.get("correction"),
        confidence=record.get("confidence"),
        outcome_id=record.get("outcome_id"),
        provenance={"source": "feedback_store"},
    )


def quality_from_record(record: Any, scope: QualityScope = QualityScope.OUTCOME) -> QualityAssessment:
    """Adapt either existing quality model without making it depend on contracts."""
    score = getattr(record, "overall_score", None)
    if score is None:
        score = getattr(record, "confidence", 0) or 0
        score = float(score) * 100 if float(score) <= 1 else float(score)
    return QualityAssessment(
        assessment_id=str(getattr(record, "assessment_id", getattr(record, "outcome_id", ""))),
        tenant_id=str(record.tenant_id),
        subject_id=str(getattr(record, "investigation_id", getattr(record, "outcome_id", ""))),
        scope=scope,
        score=float(score),
        human_review_required=bool(getattr(record, "human_review_required", True)),
        provenance=getattr(record, "provenance", {}) or {},
    )


def learning_signal_from_outcome(record: Any) -> LearningSignal:
    """Create an advisory signal from an outcome without writing to its repository."""
    outcome = outcome_from_record(record)
    confidence = getattr(record, "confidence", None)
    return LearningSignal(
        signal_id=f"outcome:{outcome.outcome_id}",
        tenant_id=outcome.tenant_id,
        signal_type="investigation_outcome",
        source_id=outcome.outcome_id,
        value={
            "status": outcome.status.value,
            "verification_status": outcome.verification_status.value,
            "case_id": outcome.case_id,
            "investigation_id": outcome.investigation_id,
            "evidence_references": list(outcome.evidence_references),
        },
        confidence=float(confidence) if confidence is not None else None,
        provenance={**outcome.provenance, "adapter": "outcome_from_record"},
    )


def learning_signal_from_feedback(feedback: Feedback) -> LearningSignal:
    """Create an advisory signal from canonical feedback without persistence."""
    if not isinstance(feedback, Feedback):
        raise TypeError("feedback_required")
    return LearningSignal(
        signal_id=f"feedback:{feedback.feedback_id}",
        tenant_id=feedback.tenant_id,
        signal_type="decision_feedback",
        source_id=feedback.feedback_id,
        value={
            "decision_id": feedback.decision_id,
            "user_id": feedback.user_id,
            "outcome": feedback.outcome.value,
            "correction": feedback.correction,
            "outcome_id": feedback.outcome_id,
        },
        confidence=feedback.confidence,
        provenance={
            **feedback.provenance,
            "adapter": "feedback_to_learning_signal",
            "feedback_id": feedback.feedback_id,
        },
    )
