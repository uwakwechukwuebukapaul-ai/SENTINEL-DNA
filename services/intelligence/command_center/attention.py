from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256

def _now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class AttentionItem:
    tenant_id: str; event_id: str; attention_type: str; priority: str; severity: str; title: str
    summary: str = ""; why_it_matters: str = ""; source_domain: str = "unknown"; source_reference: str = ""
    entity_type: str = ""; entity_reference: str = ""; investigation_reference: str = ""
    evidence_references: list = field(default_factory=list); related_event_ids: list = field(default_factory=list)
    confidence: float|None = None; uncertainty: str = "UNKNOWN"; provenance: dict = field(default_factory=dict)
    requires_human_review: bool = True; advisory: bool = True; navigation_target: dict|None = None
    created_at: str = field(default_factory=_now); updated_at: str = field(default_factory=_now)
    state: str = "new"; recurring_count: int = 1; first_seen: str = ""; last_seen: str = ""
    authoritative_priority: str = "unknown"; previous_state: str|None = None; current_state: str|None = None
    change_type: str = "unknown"; attention_id: str = ""
    def __post_init__(self):
        if not self.attention_id: self.attention_id=sha256(f"{self.tenant_id}|{self.attention_type}|{self.source_domain}|{self.source_reference}|{self.event_id}".encode()).hexdigest()[:24]
    def to_dict(self): return self.__dict__.copy()
