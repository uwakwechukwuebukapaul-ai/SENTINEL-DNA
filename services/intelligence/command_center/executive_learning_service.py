"""Read-only executive composition over historical organizational trends."""
from .executive_learning import ExecutiveLearningSignal, ExecutiveLearningSummary, stable_executive_signal_id

CLASSIFICATION_ORDER = {"critical_learning_gap": 0, "persistent_learning_gap": 1, "degrading_learning": 2, "improving_learning": 3, "emerging_learning": 4, "resolved_learning": 5, "mixed_learning": 6, "stable_learning": 7, "insufficient_data": 8}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}


class AnalystExecutiveLearningService:
    def __init__(self, trend_service=None):
        self.trend_service = trend_service

    @staticmethod
    def _v(item, key, default=None):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    @classmethod
    def _refs(cls, item):
        refs = cls._v(item, "contributing_references", []) or []
        if isinstance(refs, dict): refs = list(refs.values())
        return sorted({str(x) for x in refs if x not in (None, "")})

    def _classify(self, trend):
        source = self._v(trend, "classification", "insufficient_data")
        if source == "degrading": return "critical_learning_gap" if self._v(trend, "priority") == "high" else "degrading_learning"
        if source == "persistent": return "persistent_learning_gap"
        return {"improving": "improving_learning", "emerging": "emerging_learning", "resolved": "resolved_learning", "mixed": "mixed_learning", "stable": "stable_learning"}.get(source, "insufficient_data")

    def _priority(self, classification, trend):
        if classification == "critical_learning_gap": return "critical"
        if classification in ("persistent_learning_gap", "degrading_learning"): return "high"
        if classification in ("emerging_learning", "mixed_learning"): return "medium"
        if classification == "insufficient_data": return "informational"
        return "low"

    def derive(self, tenant_id, trends=None):
        trends = self.trend_service.derive(tenant_id) if trends is None and self.trend_service else (trends or [])
        trends = [x for x in trends if self._v(x, "tenant_id", tenant_id) == tenant_id]
        signals = []
        for trend in trends:
            classification = self._classify(trend)
            priority = self._priority(classification, trend)
            confidence = self._v(trend, "confidence")
            confidence = round(max(0.0, min(1.0, float(confidence))), 6) if confidence is not None else None
            uncertainty = sorted(set(self._v(trend, "uncertainty", []) or []))
            scope = self._v(trend, "organizational_scope")
            evidence = "strong" if confidence is not None and confidence >= .7 and not uncertainty else "moderate" if confidence is not None and confidence >= .4 else "limited"
            if classification == "insufficient_data": evidence = "insufficient"
            focus = {"critical_learning_gap": "review persistent investigation-quality gaps", "persistent_learning_gap": "review persistent investigation-quality gaps", "degrading_learning": "investigate degrading learning patterns", "improving_learning": "reinforce successful analyst practices", "emerging_learning": "monitor emerging organizational patterns", "resolved_learning": "verify that resolved patterns remain absent", "mixed_learning": "review mixed or conflicting signals", "stable_learning": "maintain evidence-backed practices", "insufficient_data": "collect additional evidence"}[classification]
            score = round(max(0.0, min(1.0, (confidence or 0.0) * (1.0 if classification in ("critical_learning_gap", "persistent_learning_gap", "degrading_learning") else .8) * (1.0 if evidence == "strong" else .7 if evidence == "moderate" else .5))), 6)
            signals.append(ExecutiveLearningSignal(tenant_id, stable_executive_signal_id(tenant_id, self._v(trend, "trend_type", "unknown"), scope), self._v(trend, "trend_type", "unknown"), self._v(trend, "title", "Organizational learning signal"), f"Executive signal derived from the observed {self._v(trend, 'classification', 'insufficient_data')} organizational trend.", classification, priority, "high" if priority in ("critical", "high") else "medium" if priority == "medium" else "low", confidence, uncertainty, evidence, self._v(trend, "direction", "unknown"), scope, self._v(trend, "organizational_dimension", "unavailable") if self._v(trend, "organizational_dimension", "unavailable") != "unavailable" else None, self._v(trend, "trend_type", "unknown"), f"Observed trend is {self._v(trend, 'classification', 'insufficient_data')}; this is not a causal claim.", self._refs(trend), self._v(trend, "provenance", {}), {"first_observed": self._v(trend, "first_observed"), "last_observed": self._v(trend, "last_observed"), "observation_count": self._v(trend, "observation_count", 0)}, focus, score))
        return sorted(signals, key=lambda x: (CLASSIFICATION_ORDER.get(x.classification, 99), PRIORITY_ORDER.get(x.priority, 99), x.signal_type, x.executive_signal_id))

    def summary(self, tenant_id, signals=None):
        signals = self.derive(tenant_id) if signals is None else [x for x in signals if self._v(x, "tenant_id", tenant_id) == tenant_id]
        count = lambda c: sum(self._v(x, "classification") == c for x in signals)
        confidences = [self._v(x, "confidence") for x in signals if self._v(x, "confidence") is not None]
        critical, degrading, improving = count("critical_learning_gap"), count("degrading_learning"), count("improving_learning")
        posture = "critical" if critical else "degrading" if degrading else "improving" if improving else "stable" if signals else "insufficient_data"
        focus = signals[0].recommended_focus if signals else "collect additional evidence"
        quality = "strong" if signals and all(self._v(x, "evidence_strength") == "strong" for x in signals) else "moderate" if signals else "insufficient"
        return ExecutiveLearningSummary(tenant_id, posture, len(signals), critical, count("persistent_learning_gap"), degrading, improving, count("emerging_learning"), count("resolved_learning"), round(sum(confidences) / len(confidences), 6) if confidences else None, quality, focus)
