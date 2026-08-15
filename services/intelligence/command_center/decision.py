"""Evidence-first, presentation-only analyst decision contexts."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

def _now(): return datetime.now(timezone.utc).isoformat()

@dataclass
class DecisionContext:
    decision_context_id: str
    tenant_id: str
    attention_id: str = ""
    event_ids: list[str] = field(default_factory=list)
    investigation_reference: str = ""
    entity_type: str = ""
    entity_reference: str = ""
    title: str = ""
    decision_question: str = "No immediate analyst decision identified."
    why_attention: str = ""
    authoritative_severity: str = "unknown"
    authoritative_priority: str = "unknown"
    attention_priority: str = "unknown"
    evidence_references: list = field(default_factory=list)
    evidence_summary: str = ""
    risk_context: Any = field(default_factory=dict)
    compliance_context: Any = field(default_factory=dict)
    governance_context: Any = field(default_factory=dict)
    lifecycle_context: Any = field(default_factory=dict)
    timeline_context: Any = field(default_factory=list)
    related_findings: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    uncertainty: bool = False
    confidence: float | None = None
    provenance: Any = field(default_factory=dict)
    requires_human_review: bool = True
    advisory: bool = True
    available_actions: list = field(default_factory=list)
    decision_state: str = "unknown"
    historical_context: Any = "unavailable"
    comparison: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self): return asdict(self)

    @staticmethod
    def stable_id(tenant_id, attention_id, investigation_reference=""):
        return sha256(f"{tenant_id}|{attention_id}|{investigation_reference}".encode()).hexdigest()[:24]

