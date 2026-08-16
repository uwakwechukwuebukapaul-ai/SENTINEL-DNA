"""Application seam from canonical feedback to advisory recommendations."""

from __future__ import annotations

from typing import Any

from services.domain_contracts import Feedback, learning_signal_from_feedback


class FeedbackRecommendationService:
    """Delegate canonical feedback recommendations to the existing optimizer."""

    def __init__(self, optimizer: Any) -> None:
        if optimizer is None or not hasattr(optimizer, "recommend_from_learning_signal"):
            raise ValueError("optimizer_required")
        self.optimizer = optimizer

    def recommend_from_feedback(self, feedback: Feedback) -> Any:
        if not isinstance(feedback, Feedback):
            raise TypeError("feedback_required")
        if not feedback.provenance:
            raise ValueError("feedback_provenance_required")
        signal = learning_signal_from_feedback(feedback)
        if not signal.advisory_only:
            raise ValueError("learning_signal_not_advisory")
        if not signal.provenance:
            raise ValueError("learning_signal_provenance_required")
        return self.optimizer.recommend_from_learning_signal(signal)
