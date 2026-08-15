"""Read-only longitudinal comparison of existing learning observations."""
from .effectiveness import AnalystLearningEffectiveness, stable_effectiveness_id

CLASSIFICATION_PRIORITY = {"improving": 0, "degrading": 1, "mixed": 2, "stable": 3, "insufficient_data": 4}


class AnalystLearningEffectivenessService:
    def __init__(self, learning_service=None, observation_provider=None):
        self.learning_service = learning_service
        self.observation_provider = observation_provider

    @staticmethod
    def _value(item, key, default=None):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    @classmethod
    def _metric(cls, item, key):
        value = cls._value(item, key)
        if value is not None:
            return float(value)
        metrics = cls._value(item, "quality_metrics", {}) or {}
        return float(metrics[key]) if key in metrics and metrics[key] is not None else None

    def _observations(self, tenant_id, observations):
        if observations is not None:
            return [x for x in observations if self._value(x, "tenant_id", tenant_id) == tenant_id]
        if self.observation_provider:
            return list(self.observation_provider(tenant_id))
        # An aggregate learning service is intentionally not treated as a time series.
        return []

    def derive(self, tenant_id, observations=None):
        rows = sorted(self._observations(tenant_id, observations), key=lambda x: (str(self._value(x, "timestamp", "")), str(self._value(x, "learning_type", "")), str(self._value(x, "learning_id", ""))))
        grouped = {}
        for row in rows:
            grouped.setdefault(self._value(row, "learning_type", "unknown"), []).append(row)
        result = []
        for learning_type, values in grouped.items():
            def refs(key):
                collected = []
                for item in values:
                    value = self._value(item, key, [])
                    collected.extend(value if isinstance(value, (list, tuple, set)) else [value])
                return sorted({str(value) for value in collected if value is not None and value != ""})
            feedback = refs("contributing_feedback_ids")
            investigations = refs("contributing_investigation_ids")
            learning_ids = refs("learning_id")
            outcomes = refs("contributing_outcome_references")
            provenance = {"source": "analyst_investigation_learning", "observation_count": len(values), "tenant_id": tenant_id}
            uncertainty = sorted({str(v) for x in values for v in (self._value(x, "uncertainty", []) or [])})
            if len(values) < 2:
                classification, score = "insufficient_data", None
                uncertainty.append("insufficient_observations")
                confidence = 0.0
                persistence = False
            else:
                midpoint = len(values) // 2
                before, after = values[:midpoint], values[midpoint:]
                if not str(self._value(before[0], "timestamp", "")) or not str(self._value(after[-1], "timestamp", "")) or str(self._value(before[-1], "timestamp", "")) >= str(self._value(after[0], "timestamp", "")):
                    classification, score = "insufficient_data", None
                    uncertainty.append("insufficient_temporal_span")
                    confidence, persistence = 0.0, False
                else:
                    persistence = True
                    metrics = ("disagreement_rate", "evidence_insufficiency_rate", "unresolved_rate", "human_review_rate", "confidence")
                    deltas = []
                    for metric in metrics:
                        left = [self._metric(x, metric) for x in before if self._metric(x, metric) is not None]
                        right = [self._metric(x, metric) for x in after if self._metric(x, metric) is not None]
                        if left and right:
                            delta = (sum(right) / len(right)) - (sum(left) / len(left))
                            if metric != "confidence": delta = -delta
                            deltas.append(delta)
                    if not deltas:
                        classification, score = "insufficient_data", None
                        uncertainty.append("insufficient_quality_observations")
                    else:
                        score = max(-1.0, min(1.0, sum(deltas) / len(deltas)))
                        positive = sum(d > 0.05 for d in deltas)
                        negative = sum(d < -0.05 for d in deltas)
                        classification = "mixed" if positive and negative else "improving" if positive else "degrading" if negative else "stable"
                    confidence = min(1.0, 0.25 + 0.1 * len(values) + (0.2 if persistence else 0))
                    if not feedback: uncertainty.append("low_feedback_coverage")
                    if not outcomes: uncertainty.append("incomplete_provenance")
            result.append(AnalystLearningEffectiveness(tenant_id, stable_effectiveness_id(tenant_id, learning_type), learning_type, classification, score, persistence, round(confidence, 6), sorted(set(uncertainty)), provenance, feedback, investigations, learning_ids, outcomes, True))
        if not result:
            result.append(AnalystLearningEffectiveness(tenant_id, stable_effectiveness_id(tenant_id, "insufficient_data"), "insufficient_data", "insufficient_data", None, False, 0.0, ["insufficient_observations", "insufficient_temporal_span"], {"source": "analyst_investigation_learning", "tenant_id": tenant_id}, [], [], [], [], True))
        return sorted(result, key=lambda x: (CLASSIFICATION_PRIORITY.get(x.classification, 99), -(x.confidence or 0), x.effectiveness_id))
