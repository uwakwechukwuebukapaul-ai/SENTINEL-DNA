"""Deterministic, advisory next-step presentation over an investigation workspace."""
from dataclasses import dataclass, asdict, field
from hashlib import sha256

@dataclass(frozen=True)
class AnalystNextStep:
    step_id: str
    tenant_id: str
    investigation_id: str
    title: str
    description: str
    reason: str
    category: str
    priority: str = "medium"
    status: str = "recommended"
    source_references: list = field(default_factory=list)
    navigation_reference: dict = field(default_factory=dict)
    confidence: float | None = None
    uncertainty: str = ""
    requires_human_review: bool = True
    advisory_only: bool = True
    def to_dict(self): return asdict(self)

def stable_step_id(tenant_id, investigation_id, category):
    return sha256(f"{tenant_id}|{investigation_id}|{category}".encode()).hexdigest()[:24]
