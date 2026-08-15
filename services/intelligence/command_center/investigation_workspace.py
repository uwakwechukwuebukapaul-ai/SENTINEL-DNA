"""Read-only composition of Command Center investigation context."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

def _now(): return datetime.now(timezone.utc).isoformat()
def _dict(value): return value.to_dict() if hasattr(value, "to_dict") else value

@dataclass
class AnalystInvestigationWorkspace:
    tenant_id: str
    investigation: dict = field(default_factory=dict)
    attention: dict | None = None
    events: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    decision: dict | None = None
    navigation: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    uncertainty: str = "UNKNOWN"
    requires_human_review: bool = True
    subsystem_availability: dict = field(default_factory=dict)
    generated_at: str = field(default_factory=_now)
    advisory: bool = True
    def to_dict(self): return asdict(self)

class AnalystInvestigationWorkspaceService:
    """Tenant-scoped presentation composition; authoritative sources remain external."""
    def __init__(self, event_feed=None, attention_service=None, decision_service=None, source_resolver=None):
        self.event_feed = event_feed; self.attention_service = attention_service; self.decision_service = decision_service; self.source_resolver = source_resolver
    def _source(self, tenant_id, kind, reference):
        if not self.source_resolver or not reference: return None
        value = self.source_resolver(tenant_id, kind, str(reference))
        return dict(value) if value and value.get("tenant_id", tenant_id) == tenant_id else None
    def build(self, tenant_id, investigation_id):
        investigation = self._source(tenant_id, "investigation", investigation_id)
        if not investigation: return None
        events = self.event_feed.events(tenant_id, investigation_id=str(investigation_id)) if self.event_feed else []
        attention = None
        if self.attention_service:
            values = self.attention_service.get_attention_queue(tenant_id, investigation_reference=str(investigation_id)); attention = values[0].to_dict() if values else None
        decision = None
        if self.decision_service:
            values = self.decision_service.by_investigation(tenant_id, str(investigation_id))
            if values: decision = _dict(values[0])
            elif attention and attention.get("attention_id"):
                value = self.decision_service.derive(tenant_id, attention["attention_id"]); decision = _dict(value) if value else None
        references = list(investigation.get("evidence_references", []) or [])
        if attention: references += list(attention.get("evidence_references", []) or [])
        if decision: references += list(decision.get("evidence_references", []) or [])
        evidence=[]; unavailable=[]
        for reference in dict.fromkeys(str(x) for x in references if x):
            value=self._source(tenant_id, "evidence", reference)
            if value: evidence.append(value)
            else: unavailable.append({"evidence_id":reference,"status":"unavailable","uncertainty":"UNKNOWN","requires_human_review":True})
        evidence.extend(unavailable); all_events=[_dict(x) for x in events]
        uncertain=bool(unavailable) or any(str(x.get("uncertainty", "")).upper() not in {"", "NONE", "FALSE", "KNOWN"} for x in all_events)
        review=bool(unavailable or uncertain or investigation.get("requires_human_review", True) or (decision and decision.get("requires_human_review", True)))
        provenance={"investigation":investigation.get("provenance", {}),"events":[x.get("provenance", {}) for x in all_events],"evidence":[x.get("provenance", {}) for x in evidence]}
        navigation={"investigation":{"type":"investigation","reference":str(investigation_id)},"events":[{"type":"event","reference":x.get("event_id")} for x in all_events],"evidence":[{"type":"evidence","reference":x.get("evidence_id",x.get("id"))} for x in evidence],"history":{"type":"history","reference":str(investigation_id)}}
        if attention: navigation["attention"]={"type":"attention","reference":attention.get("attention_id")}
        if decision: navigation["decision"]={"type":"decision","reference":decision.get("decision_context_id")}
        availability={"investigation":"AVAILABLE","events":"AVAILABLE" if self.event_feed else "UNAVAILABLE","attention":"AVAILABLE" if self.attention_service else "UNAVAILABLE","evidence":"DEGRADED" if unavailable else "AVAILABLE","decision":"AVAILABLE" if decision else "UNAVAILABLE"}
        return AnalystInvestigationWorkspace(tenant_id, investigation, attention, all_events, evidence, decision, navigation, provenance, "TRUE" if uncertain else "", review, availability)
