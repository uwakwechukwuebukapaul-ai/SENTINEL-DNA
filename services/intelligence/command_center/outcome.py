"""Deterministic analytical investigation outcomes; never case or lifecycle state."""
from dataclasses import dataclass, asdict, field
from hashlib import sha256

@dataclass(frozen=True)
class InvestigationOutcome:
    investigation_id: str
    tenant_id: str
    outcome_id: str
    outcome_category: str
    outcome_status: str
    confidence: float | None = None
    uncertainty: list = field(default_factory=list)
    supporting_evidence: list = field(default_factory=list)
    decision_references: list = field(default_factory=list)
    event_references: list = field(default_factory=list)
    unresolved_items: list = field(default_factory=list)
    requires_human_review: bool = True
    provenance: dict = field(default_factory=dict)
    advisory_only: bool = True
    def to_dict(self): return asdict(self)

def stable_outcome_id(tenant_id, investigation_id):
    return sha256(f"{tenant_id}|{investigation_id}|outcome".encode()).hexdigest()[:24]
