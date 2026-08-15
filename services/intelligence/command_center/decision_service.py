from .decision import DecisionContext
from .decision_repository import DecisionContextRepository

class AnalystDecisionContextService:
    def __init__(self, attention_service=None, repository=None):
        self.attention_service = attention_service
        self.repository = repository or DecisionContextRepository()

    def _question(self, attention):
        kind = getattr(attention, "attention_type", "")
        return {"risk_change": "Review whether the investigation should be escalated.",
                "insufficient_evidence": "Determine whether the evidence is sufficient to continue investigation.",
                "compliance_drift": "Review whether the observed compliance drift requires further investigation.",
                "governance_review": "Determine whether the governance decision requires human approval.",
                "lifecycle_review": "Review whether the lifecycle state can move to the next governed stage."}.get(kind, "No immediate analyst decision identified.")

    def from_attention(self, tenant_id, attention):
        evidence = list(getattr(attention, "evidence_references", []) or [])
        uncertain = str(getattr(attention, "uncertainty", "UNKNOWN")).upper() not in {"", "NONE", "FALSE", "KNOWN"}
        if not evidence:
            uncertain = True
        state = "insufficient_evidence" if not evidence else ("pending_review" if getattr(attention, "requires_human_review", True) else "decision_ready")
        ref = getattr(attention, "investigation_reference", "") or ""
        ctx = DecisionContext(DecisionContext.stable_id(tenant_id, attention.attention_id, ref), tenant_id,
            attention_id=attention.attention_id, event_ids=list(getattr(attention, "related_event_ids", []) or []),
            investigation_reference=ref, entity_type=getattr(attention, "entity_type", ""), entity_reference=getattr(attention, "entity_reference", ""),
            title=getattr(attention, "title", ""), decision_question=self._question(attention), why_attention=getattr(attention, "why_it_matters", ""),
            authoritative_severity=getattr(attention, "severity", "unknown"), authoritative_priority=getattr(attention, "authoritative_priority", "unknown"),
            attention_priority=getattr(attention, "priority", "unknown"), evidence_references=evidence,
            evidence_summary=("Available evidence is insufficient." if not evidence else getattr(attention, "summary", "")),
            uncertainty=uncertain, confidence=getattr(attention, "confidence", None), provenance=getattr(attention, "provenance", {}) or {},
            requires_human_review=True, advisory=True, decision_state=state)
        return self.repository.save(ctx)

    def derive(self, tenant_id, attention_id=None):
        if not self.attention_service: return None if attention_id else []
        items = ([self.attention_service.get_attention(tenant_id, attention_id)] if attention_id else self.attention_service.get_attention_queue(tenant_id))
        items = [x for x in items if x]
        return [self.from_attention(tenant_id, x) for x in items] if not attention_id else self.from_attention(tenant_id, items[0]) if items else None
    def get(self, tenant_id, context_id): return self.repository.get(tenant_id, context_id)
    def latest(self, tenant_id): return self.repository.get_latest(tenant_id)
    def history(self, tenant_id): return self.repository.get_history(tenant_id)
    def by_attention(self, tenant_id, attention_id): return self.repository.get_by_attention(tenant_id, attention_id)
    def by_investigation(self, tenant_id, investigation_id): return self.repository.get_by_investigation(tenant_id, investigation_id)

