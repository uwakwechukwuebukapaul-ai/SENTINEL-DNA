"""Read-only aggregation of existing Command Center learning intelligence."""
from .organizational_learning import OrganizationalLearning, stable_organizational_learning_id

PATTERN_MAP = {
    "repeated_disagreement": ("recurring_organizational_disagreement", "Recurring organizational disagreement", "review investigations with repeated analyst disagreement"),
    "evidence_gap": ("recurring_evidence_gaps", "Recurring organizational evidence gaps", "improve evidence collection completeness"),
    "unresolved_pattern": ("recurring_unresolved_investigations", "Recurring unresolved investigations", "prioritize unresolved investigations for human review"),
    "human_review_pattern": ("recurring_human_review_dependency", "Recurring human-review dependency", "review recurring human-review cases"),
    "low_confidence_pattern": ("recurring_low_confidence", "Recurring low-confidence investigations", "examine consistently low-confidence investigations"),
    "uncertainty_pattern": ("recurring_uncertainty", "Recurring investigation uncertainty", "review cases with persistent uncertainty"),
    "quality_degradation": ("organizational_quality_degradation", "Organizational quality degradation", "review degrading quality signals"),
    "positive_quality_pattern": ("organizational_quality_improvement", "Organizational quality improvement", "preserve evidence-backed investigation practices"),
}
ORDER = {"improving": 0, "degrading": 1, "mixed": 2, "stable": 3, "new_pattern": 4, "resolved_pattern": 5, "persistent_pattern": 6, "insufficient_data": 7}


class OrganizationalLearningService:
    def __init__(self, learning_service=None, effectiveness_service=None, feedback_service=None):
        self.learning_service, self.effectiveness_service, self.feedback_service = learning_service, effectiveness_service, feedback_service

    @staticmethod
    def _v(item, key, default=None):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    @staticmethod
    def _refs(items, key):
        values = []
        for item in items:
            value = OrganizationalLearningService._v(item, key, []) if item else []
            values.extend(value if isinstance(value, (list, tuple, set)) else [value])
        return sorted({str(v) for v in values if v is not None and v != ""})

    def derive(self, tenant_id, learning=None, effectiveness=None, feedback=None):
        learning = learning if learning is not None else (self.learning_service.derive(tenant_id) if self.learning_service else [])
        effectiveness = effectiveness if effectiveness is not None else (self.effectiveness_service.derive(tenant_id) if self.effectiveness_service else [])
        feedback = feedback if feedback is not None else (self.feedback_service.derive(tenant_id) if self.feedback_service else [])
        learning = [x for x in learning if self._v(x, "tenant_id", tenant_id) == tenant_id]
        effectiveness = [x for x in effectiveness if self._v(x, "tenant_id", tenant_id) == tenant_id]
        feedback = [x for x in feedback if self._v(x, "tenant_id", tenant_id) == tenant_id]
        by_kind = {self._v(x, "learning_type"): x for x in learning}
        rows = []
        for item in learning:
            kind = self._v(item, "learning_type", "unknown")
            pattern, title, focus = PATTERN_MAP.get(kind, (kind, self._v(item, "title", kind), self._v(item, "recommended_analyst_focus", "review the evidence-backed organizational pattern")))
            eff = next((x for x in effectiveness if self._v(x, "learning_type") == kind), None)
            fb = next((x for x in feedback if self._v(x, "learning_type") == kind), None)
            classification = self._v(fb, "state") or self._v(eff, "classification") or "insufficient_data"
            if classification not in ORDER: classification = "insufficient_data"
            refs = [item, eff, fb]
            uncertainty = sorted({str(v) for x in refs if x for v in (self._v(x, "uncertainty", []) or [])})
            confidence_values = [self._v(x, "confidence") for x in refs if x and self._v(x, "confidence") is not None]
            confidence = round(sum(confidence_values) / len(confidence_values), 6) if confidence_values else None
            provenance = {"source": "organizational_learning", "upstream": ["analyst_investigation_learning", "analyst_learning_effectiveness", "analyst_learning_feedback"], "tenant_id": tenant_id}
            rows.append(OrganizationalLearning(tenant_id, stable_organizational_learning_id(tenant_id, pattern, classification), pattern, classification, title, f"Organizational intelligence identifies {title.lower()} from tenant-scoped learning evidence.", confidence, uncertainty, provenance, self._refs(refs, "contributing_investigation_ids"), self._refs(refs, "contributing_feedback_ids"), self._refs(refs, "contributing_learning_ids") + ([str(self._v(item, "learning_id"))] if self._v(item, "learning_id") else []), self._refs(refs, "effectiveness_id"), focus))
        known = {self._v(x, "learning_type") for x in learning}
        for item in feedback:
            kind = self._v(item, "learning_type", "unknown")
            if kind in known:
                continue
            state = self._v(item, "state", "insufficient_data")
            pattern, title, focus = PATTERN_MAP.get(kind, (kind, f"Organizational {kind}", "review the evidence-backed organizational pattern"))
            rows.append(OrganizationalLearning(tenant_id, stable_organizational_learning_id(tenant_id, pattern, state), pattern, state if state in ORDER else "insufficient_data", title, "Organizational feedback identifies a pattern not present in the current learning snapshot.", self._v(item, "confidence"), sorted(set(self._v(item, "uncertainty", []) or [])), {"source": "organizational_learning", "upstream": ["analyst_learning_feedback"], "tenant_id": tenant_id}, self._refs([item], "contributing_investigation_ids"), self._refs([item], "contributing_feedback_ids"), self._refs([item], "contributing_learning_ids"), [], focus))
        if not rows:
            rows.append(OrganizationalLearning(tenant_id, stable_organizational_learning_id(tenant_id, "insufficient_organizational_data", "insufficient_data"), "insufficient_organizational_data", "insufficient_data", "Insufficient organizational learning data", "No tenant-scoped learning observations are available for organizational interpretation.", 0.0, ["insufficient_organizational_data"], {"source": "organizational_learning", "upstream": ["analyst_investigation_learning", "analyst_learning_effectiveness", "analyst_learning_feedback"], "tenant_id": tenant_id}, [], [], [], [], "collect structured investigation-quality observations"))
        return sorted(rows, key=lambda x: (ORDER.get(x.classification, 99), x.pattern_type, x.organizational_learning_id))
