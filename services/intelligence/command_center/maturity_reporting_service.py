"""Historical, read-only analytics over canonical maturity observations."""
from .maturity_reporting import MaturityReport, stable_report_id

ORDER = {"degrading": 0, "mixed": 1, "improving": 2, "stable": 3, "insufficient_data": 4}


class MaturityReportingService:
    def __init__(self, maturity_service=None): self.maturity_service = maturity_service
    @staticmethod
    def _v(x, k, d=None): return x.get(k, d) if isinstance(x, dict) else getattr(x, k, d)
    @classmethod
    def _refs(cls, rows): return sorted({str(v) for x in rows for v in (cls._v(x, "contributing_references", []) or []) + (cls._v(x, "contributing_investigation_ids", []) or []) + (cls._v(x, "contributing_feedback_ids", []) or []) if v not in (None, "")})

    def derive(self, tenant_id, current=None, observations=None):
        current = current if current is not None else (self.maturity_service.derive(tenant_id) if self.maturity_service else None)
        history = sorted([x for x in (observations or []) if self._v(x, "tenant_id", tenant_id) == tenant_id], key=lambda x: (str(self._v(x, "timestamp", self._v(x, "observed_at", ""))), str(self._v(x, "score", ""))))
        score = self._v(current, "maturity_score") if current else None; level = self._v(current, "maturity_level", "insufficient_data") if current else "insufficient_data"
        previous = history[-1] if history else None
        previous_score = self._v(previous, "maturity_score", self._v(previous, "score")) if previous else None
        previous_level = self._v(previous, "maturity_level", self._v(previous, "level")) if previous else None
        timestamps = [str(self._v(x, "timestamp", self._v(x, "observed_at", ""))) for x in history]
        temporal = f"{timestamps[0]}..{timestamps[-1]}" if len(history) > 1 and all(timestamps) else ""
        uncertainty = sorted(set((self._v(current, "uncertainty", []) if current else []) + (["insufficient historical observations"] if len(history) < 2 else []) + (["insufficient temporal span"] if len(history) >= 2 and not temporal else [])))
        delta = round(score - previous_score, 2) if score is not None and previous_score is not None else None
        if len(history) < 2: trajectory = "insufficient_data"
        elif delta is None: trajectory = "insufficient_data"
        elif delta > 2: trajectory = "improving"
        elif delta < -2: trajectory = "degrading"
        else: trajectory = "stable"
        if trajectory == "improving" and len(history) >= 3: trajectory = "sustained_improvement"
        if trajectory == "degrading" and len(history) >= 3: trajectory = "sustained_degradation"
        transition = "maturity_transition" if previous_level and level != previous_level else "none"
        dimensions = self._v(current, "dimensions", []) if current else []
        summaries = [x.to_dict() if hasattr(x, "to_dict") else dict(x) for x in dimensions]
        strongest = sorted([x for x in summaries if x.get("score") is not None], key=lambda x: (-x["score"], x.get("dimension_id", "")))[:3]
        weakest = sorted([x for x in summaries if x.get("score") is not None], key=lambda x: (x["score"], x.get("dimension_id", "")))[:3]
        recommendations = ([{"priority": "high", "recommendation": "Monitor degrading organizational capability", "rationale": "Historical maturity score is declining."}] if "degrad" in trajectory else [{"priority": "medium", "recommendation": "Reinforce practices associated with improving outcomes", "rationale": "Historical maturity score is improving."}] if "improv" in trajectory else [{"priority": "medium", "recommendation": "Establish additional temporal observations before making a maturity determination", "rationale": "Historical maturity evidence is limited."}])
        interpretation = "degrading" if "degrad" in trajectory else "strong and improving" if "improv" in trajectory else "stable with limited historical evidence" if trajectory == "stable" else "insufficient historical evidence"
        confidence = self._v(current, "confidence") if current else None
        return MaturityReport(tenant_id, stable_report_id(tenant_id), score, previous_score, delta, level, previous_level, trajectory, transition, summaries, strongest, weakest, [], [], [], [], self._v(current, "evidence_strength", "insufficient") if current else "insufficient", confidence, uncertainty, {"source": "maturity_reporting", "upstream": ["organizational_maturity", "organizational_trends"], "tenant_id": tenant_id}, self._refs([current] if current else []) + self._refs(history), recommendations, len(history), temporal, interpretation, "unavailable")
