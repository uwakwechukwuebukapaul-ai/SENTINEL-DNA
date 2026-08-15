from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

def now(): return datetime.now(timezone.utc).isoformat()

@dataclass
class AttentionItem:
    tenant_id: str; category: str; priority: str; severity: str; confidence: float|None
    title: str; rationale: str; evidence_references: list = field(default_factory=list)
    source_reference: str = ""; requires_human_review: bool = True; timestamp: str = field(default_factory=now)
    provenance: dict = field(default_factory=dict); attention_id: str = field(default_factory=lambda: str(uuid4()))
    def to_dict(self): return self.__dict__.copy()

@dataclass
class DecisionItem:
    tenant_id: str; category: str; title: str; current_state: str = "UNKNOWN"
    recommended_next_review_step: str = "Review source context"
    supporting_evidence: list = field(default_factory=list); confidence: float|None = None
    uncertainty: str = "UNKNOWN"; provenance: dict = field(default_factory=dict)
    approval_required: bool = False; lifecycle_state: str = "UNKNOWN"; source_reference: str = ""
    decision_id: str = field(default_factory=lambda: str(uuid4())); advisory: bool = True
    requires_human_review: bool = True
    def to_dict(self): return self.__dict__.copy()

@dataclass
class CommandSnapshot:
    tenant_id: str; generated_at: str = field(default_factory=now); platform_health: dict = field(default_factory=dict)
    active_investigations: list = field(default_factory=list); critical_findings: list = field(default_factory=list)
    subsystem_availability: dict = field(default_factory=dict); uncertainty: str = "UNKNOWN"
    attention_items: list = field(default_factory=list); decision_items: list = field(default_factory=list)
    executive_summary: dict = field(default_factory=dict)
    def to_dict(self): return self.__dict__.copy()
