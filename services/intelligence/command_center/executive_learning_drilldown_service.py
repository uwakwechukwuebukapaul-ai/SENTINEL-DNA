"""Read-only composition of executive signals and supporting intelligence."""
from .executive_learning_drilldown import ExecutiveLearningDrillDown


class ExecutiveLearningDrillDownService:
    def __init__(self, executive_service=None, trend_service=None, learning_service=None, effectiveness_service=None, feedback_service=None, organizational_learning_service=None):
        self.executive_service, self.trend_service = executive_service, trend_service
        self.learning_service, self.effectiveness_service = learning_service, effectiveness_service
        self.feedback_service, self.organizational_learning_service = feedback_service, organizational_learning_service

    @staticmethod
    def _v(item, key, default=None):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    @classmethod
    def _safe(cls, item):
        return item.to_dict() if hasattr(item, "to_dict") else dict(item) if isinstance(item, dict) else {}

    @classmethod
    def _refs(cls, rows):
        values = []
        for row in rows:
            for key in ("contributing_references", "contributing_investigation_ids", "contributing_feedback_ids", "contributing_learning_ids", "contributing_effectiveness_ids"):
                value = cls._v(row, key, []) if row else []
                values.extend(value if isinstance(value, (list, tuple, set)) else [value])
        return [{"reference": str(v)} for v in sorted({str(v) for v in values if v not in (None, "")})]

    def get(self, tenant_id, signal_id, trends=None, signals=None, learning=None, effectiveness=None, feedback=None, organizational_learning=None):
        signals = signals if signals is not None else (self.executive_service.derive(tenant_id) if self.executive_service else [])
        signals = [x for x in signals if self._v(x, "tenant_id", tenant_id) == tenant_id]
        signal = next((x for x in signals if self._v(x, "executive_signal_id") == str(signal_id)), None)
        if signal is None:
            return None
        trend_type = self._v(signal, "signal_type")
        trends = trends if trends is not None else (self.trend_service.derive(tenant_id) if self.trend_service else [])
        trends = [x for x in trends if self._v(x, "tenant_id", tenant_id) == tenant_id]
        trend = next((x for x in trends if self._v(x, "trend_type") == trend_type), None)
        learning = learning if learning is not None else (self.learning_service.derive(tenant_id) if self.learning_service else [])
        effectiveness = effectiveness if effectiveness is not None else (self.effectiveness_service.derive(tenant_id) if self.effectiveness_service else [])
        feedback = feedback if feedback is not None else (self.feedback_service.derive(tenant_id) if self.feedback_service else [])
        organizational_learning = organizational_learning if organizational_learning is not None else (self.organizational_learning_service.derive(tenant_id) if self.organizational_learning_service else [])
        def matching(items): return [x for x in items if self._v(x, "tenant_id", tenant_id) == tenant_id and self._v(x, "learning_type", self._v(x, "pattern_type")) == trend_type]
        related_learning, related_effectiveness, related_feedback, related_org = matching(learning), matching(effectiveness), matching(feedback), matching(organizational_learning)
        evidence = [signal, trend] + related_learning + related_effectiveness + related_feedback + related_org
        classification = self._v(signal, "classification", "insufficient_data")
        interpretations = {"critical_learning_gap": "A critical organizational learning gap is present in the available evidence.", "persistent_learning_gap": "Persistent learning signals indicate that this organizational area has not demonstrated sustained improvement across the observed period.", "degrading_learning": "Observed degrading learning signals indicate worsening movement across the available period.", "improving_learning": "Observed improving learning signals indicate positive movement across the available period.", "emerging_learning": "An emerging organizational learning pattern is present in the current evidence.", "resolved_learning": "The previously observed learning pattern is currently resolved in the available evidence.", "mixed_learning": "Mixed learning signals indicate conflicting movement across the available evidence.", "stable_learning": "Stable learning signals show no material directional movement in the available evidence.", "insufficient_data": "Insufficient historical evidence is available for a stronger executive interpretation."}
        dimensions = []
        for key in ("organizational_scope", "organizational_dimension", "team_focus"):
            value = self._v(signal, key) or self._v(trend, key) if trend else self._v(signal, key)
            if value and value != "unavailable": dimensions.append({"dimension": key, "value": value, "evidence_count": len(evidence)})
        if not any(x["dimension"] in ("team_focus", "team") for x in dimensions): dimensions.append({"dimension": "team", "value": None, "evidence_count": 0, "uncertainty": "Team attribution unavailable"})
        uncertainty = sorted({str(v) for x in evidence if x for v in (self._v(x, "uncertainty", []) or [])})
        return ExecutiveLearningDrillDown(tenant_id, str(signal_id), self._safe(signal), self._safe(trend) if trend else None, dimensions, [self._safe(x) for x in related_org or related_learning], [self._safe(x) for x in related_effectiveness], [self._safe(x) for x in related_feedback], self._refs(evidence), interpretations.get(classification, interpretations["insufficient_data"]), self._v(signal, "recommended_focus", "Collect additional evidence"), self._v(signal, "confidence"), uncertainty, {"source": "executive_learning_drilldown", "upstream": ["executive_learning", "organizational_trend", "organizational_learning", "learning_effectiveness", "learning_feedback"], "tenant_id": tenant_id})
