"""Deterministic, read-only internal maturity aggregation."""
from .maturity import MaturityDimension, OrganizationalMaturity

LEVELS = ((0, "insufficient_data"), (40, "Emerging"), (60, "Developing"), (75, "Established"), (90, "Advanced"), (101, "Optimized"))
ORDER = {"critical_maturity_gap": 0, "persistent_degradation": 1, "insufficient_evidence": 2, "mixed_capability": 3, "emerging_capability": 4, "improving_capability": 5, "stable_capability": 6, "strong_learning_capability": 7}


class OrganizationalMaturityService:
    def __init__(self, organizational_learning_service=None, trend_service=None, effectiveness_service=None, feedback_service=None, executive_service=None):
        self.org_service, self.trend_service = organizational_learning_service, trend_service
        self.effectiveness_service, self.feedback_service, self.executive_service = effectiveness_service, feedback_service, executive_service

    @staticmethod
    def _v(x, k, d=None): return x.get(k, d) if isinstance(x, dict) else getattr(x, k, d)
    @staticmethod
    def _level(score):
        if score is None: return "insufficient_data"
        return next(level for floor, level in reversed(LEVELS) if score >= floor)
    @classmethod
    def _refs(cls, rows):
        return sorted({str(v) for x in rows for v in (cls._v(x, "contributing_investigation_ids", []) or []) + (cls._v(x, "contributing_feedback_ids", []) or []) + (cls._v(x, "contributing_learning_ids", []) or []) if v not in (None, "")})

    def derive(self, tenant_id, organizational_learning=None, trends=None, effectiveness=None, feedback=None, executive_signals=None, historical_scores=None):
        org = organizational_learning if organizational_learning is not None else (self.org_service.derive(tenant_id) if self.org_service else [])
        org = [x for x in org if self._v(x, "tenant_id", tenant_id) == tenant_id]
        trends = trends if trends is not None else (self.trend_service.derive(tenant_id) if self.trend_service else [])
        trends = [x for x in trends if self._v(x, "tenant_id", tenant_id) == tenant_id]
        dimensions = []
        for item in org:
            classification = self._v(item, "classification", "insufficient_data")
            score = {"improving": 78, "stable": 68, "persistent_pattern": 42, "degrading": 30, "mixed": 50, "new_pattern": 45, "resolved_pattern": 70, "insufficient_data": None}.get(classification, 55)
            uncertainty = sorted(set(self._v(item, "uncertainty", []) or []))
            confidence = self._v(item, "confidence")
            strength = "strong" if confidence is not None and confidence >= .7 and not uncertainty else "moderate" if confidence is not None and confidence >= .4 else "limited" if confidence is not None else "insufficient"
            dimensions.append(MaturityDimension(self._v(item, "learning_type", "organizational_learning"), self._v(item, "title", "Organizational Learning"), self._level(score), score, classification, confidence, strength, uncertainty, self._v(item, "investigation_count", 0), "", self._refs([item]), {"source": "organizational_maturity", "upstream": ["organizational_learning", "organizational_trends", "learning_effectiveness", "learning_feedback"], "tenant_id": tenant_id}))
        if not dimensions:
            return OrganizationalMaturity(tenant_id, None, "insufficient_data", "insufficient_data", [], [{"signal_type": "insufficient_evidence", "priority": "informational", "title": "Insufficient maturity evidence"}], None, None, "insufficient_history", "insufficient_data", 0.0, "insufficient", ["insufficient observations"], 0, "", [], {"source": "organizational_maturity", "tenant_id": tenant_id}, ["Establish additional temporal observations before making a maturity determination."], "unavailable")
        scores = [x.score for x in dimensions if x.score is not None]; score = round(sum(scores) / len(scores), 2) if scores else None
        trend_states = [self._v(x, "classification", "insufficient_data") for x in trends]
        trend = "degrading" if "degrading" in trend_states else "improving" if "improving" in trend_states else "mixed" if "mixed" in trend_states else "stable" if trend_states else "insufficient_data"
        baseline = round(sum(historical_scores) / len(historical_scores), 2) if historical_scores else None
        status = "above_historical_baseline" if baseline is not None and score > baseline + 5 else "below_historical_baseline" if baseline is not None and score < baseline - 5 else "near_historical_baseline" if baseline is not None else "insufficient_history"
        signals = []
        if any(x.classification == "degrading" for x in dimensions): signals.append({"signal_type": "persistent_degradation", "priority": "high", "title": "Degrading organizational capability"})
        if any(x.classification in ("persistent_pattern", "evidence_gap") for x in dimensions): signals.append({"signal_type": "persistent_learning_gap", "priority": "high", "title": "Persistent learning gap"})
        if trend == "improving": signals.append({"signal_type": "improving_capability", "priority": "low", "title": "Improving investigation-learning capability"})
        signals.sort(key=lambda x: (ORDER.get(x["signal_type"], 99), x["signal_type"]))
        confidence_values = [x.confidence for x in dimensions if x.confidence is not None]; confidence = round(sum(confidence_values) / len(confidence_values), 6) if confidence_values else None
        uncertainty = sorted({u for x in dimensions for u in x.uncertainty}); strength = "strong" if confidence is not None and confidence >= .7 and not uncertainty else "moderate" if confidence is not None and confidence >= .4 else "limited"
        recommendations = ["Review persistent learning gaps."] if any(s["signal_type"] == "persistent_learning_gap" for s in signals) else ["Reinforce practices associated with improving outcomes."] if trend == "improving" else ["Establish additional temporal observations before making a maturity determination."] if baseline is None else []
        return OrganizationalMaturity(tenant_id, score, self._level(score), "improving" if trend == "improving" else "degrading" if trend == "degrading" else "stable" if trend == "stable" else "mixed", dimensions, signals, baseline, round(score - baseline, 2) if baseline is not None else None, status, trend, confidence, strength, uncertainty, sum(self._v(x, "investigation_count", 0) or 0 for x in org), "", sorted(set(self._refs(org))), {"source": "organizational_maturity", "upstream": ["organizational_learning", "organizational_trends", "learning_effectiveness", "learning_feedback", "executive_learning"], "tenant_id": tenant_id}, recommendations, "unavailable")
