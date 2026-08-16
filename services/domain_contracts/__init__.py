"""Stable, serializable domain contracts shared across intelligence services."""

from .models import (
    Feedback,
    FeedbackOutcome,
    LearningSignal,
    QualityAssessment,
    QualityScope,
    Outcome,
    OutcomeStatus,
)
from .adapters import feedback_from_store_record, outcome_from_record, quality_from_record

__all__ = [
    "Feedback",
    "FeedbackOutcome",
    "LearningSignal",
    "QualityAssessment",
    "QualityScope",
    "Outcome",
    "OutcomeStatus",
    "feedback_from_store_record",
    "outcome_from_record",
    "quality_from_record",
]
