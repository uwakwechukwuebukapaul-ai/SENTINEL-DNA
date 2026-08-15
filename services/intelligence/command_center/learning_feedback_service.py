"""Read-only deterministic feedback loop over learning and effectiveness."""
from .learning_feedback import AnalystLearningFeedback, stable_learning_feedback_id

STATE_PRIORITY = {"improving": 0, "degrading": 1, "mixed": 2, "stable": 3, "new_pattern": 4, "resolved_pattern": 5, "persistent_pattern": 6, "insufficient_data": 7}


class AnalystLearningFeedbackService:
    def __init__(self, learning_service=None, effectiveness_service=None):
        self.learning_service = learning_service
        self.effectiveness_service = effectiveness_service

    @staticmethod
    def _value(item, key, default=None):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    def derive(self, tenant_id, learning_observations=None, effectiveness_observations=None, previous_learning_observations=None):
        learning_observations = (self.learning_service.derive(tenant_id) if learning_observations is None and self.learning_service else (learning_observations or []))
        effectiveness_observations = (self.effectiveness_service.derive(tenant_id) if effectiveness_observations is None and self.effectiveness_service else (effectiveness_observations or []))
        current = {self._value(x, "learning_type"): x for x in learning_observations if self._value(x, "tenant_id", tenant_id) == tenant_id}
        previous = {self._value(x, "learning_type"): x for x in (previous_learning_observations or []) if self._value(x, "tenant_id", tenant_id) == tenant_id}
        rows = []
        for item in effectiveness_observations:
            if self._value(item, "tenant_id", tenant_id) != tenant_id: continue
            kind, effectiveness = self._value(item, "learning_type", "unknown"), self._value(item, "classification", "insufficient_data")
            if kind not in current and kind in previous: state, changed, why = "resolved_pattern", "The learning pattern is no longer present.", "It was present in the prior learning snapshot but not the current snapshot."
            elif kind not in previous and previous: state, changed, why = "new_pattern", "A learning pattern appears for the first time in the comparison.", "The pattern is present currently but absent from the prior learning snapshot."
            elif effectiveness == "insufficient_data": state, changed, why = "insufficient_data", "Effectiveness cannot be determined.", "The upstream effectiveness result reports insufficient evidence."
            elif self._value(item, "persistence", False): state, changed, why = "persistent_pattern", "The learning pattern persists across evaluation observations.", "The effectiveness service reports a persistent temporal pattern."
            else: state, changed, why = effectiveness, f"The learning pattern is {effectiveness}.", f"The upstream effectiveness classification is {effectiveness}."
            learning = current.get(kind) or previous.get(kind)
            uncertainty = sorted(set((self._value(item, "uncertainty", []) or []) + (self._value(learning, "uncertainty", []) or [])))
            provenance = {"source": "analyst_learning_feedback", "upstream": ["analyst_investigation_learning", "analyst_learning_effectiveness"], "tenant_id": tenant_id}
            rows.append(AnalystLearningFeedback(tenant_id, stable_learning_feedback_id(tenant_id, kind, state), kind, state, changed, why, effectiveness, self._value(item, "confidence"), uncertainty, provenance, sorted(set(self._value(item, "contributing_feedback_ids", []) or [])), sorted(set(self._value(item, "contributing_investigation_ids", []) or [])), sorted(set(self._value(item, "contributing_learning_ids", []) or [])), self._value(learning, "recommended_analyst_focus", "review the evidence-backed learning pattern")))
        return sorted(rows, key=lambda x: (STATE_PRIORITY.get(x.state, 99), x.learning_type, x.feedback_id))
