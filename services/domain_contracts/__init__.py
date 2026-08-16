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
from .adapters import feedback_from_store_record, learning_signal_from_outcome, outcome_from_record, quality_from_record
from .persistence import OutcomePersistenceBoundary
from .investigation_feedback import InvestigationFeedback
from .investigation_feedback_adapter import InvestigationFeedbackAdapter
from .feedback_boundary import FeedbackReadBoundary
from .decision_feedback_boundary import DecisionFeedbackWriteBoundary

__all__ = [
    "Feedback",
    "FeedbackOutcome",
    "LearningSignal",
    "QualityAssessment",
    "QualityScope",
    "Outcome",
    "OutcomeStatus",
    "feedback_from_store_record",
    "learning_signal_from_outcome",
    "outcome_from_record",
    "quality_from_record",
    "OutcomePersistenceBoundary",
    "InvestigationFeedback",
    "InvestigationFeedbackAdapter",
    "FeedbackReadBoundary",
    "DecisionFeedbackWriteBoundary",
]
