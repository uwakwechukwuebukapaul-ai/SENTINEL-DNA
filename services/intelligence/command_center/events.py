from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json

def _now(): return datetime.now(timezone.utc).isoformat()

@dataclass
class AnalystEvent:
    tenant_id: str; event_type: str; category: str; title: str; summary: str = ""
    source_domain: str = "unknown"; source_reference: str = ""; entity_type: str = ""; entity_reference: str = ""
    severity: str = "unknown"; priority: str = "medium"; timestamp: str = field(default_factory=_now)
    confidence: float|None = None; uncertainty: str = "UNKNOWN"; provenance: dict = field(default_factory=dict)
    requires_human_review: bool = True; advisory: bool = True; navigation_target: dict|None = None
    event_id: str = ""; acknowledgement: str = "new"; related: dict = field(default_factory=dict)
    def __post_init__(self):
        if not self.event_id:
            key=json.dumps([self.tenant_id,self.source_domain,self.source_reference,self.event_type,self.timestamp],separators=(",",":"))
            self.event_id=sha256(key.encode()).hexdigest()[:24]
    def to_dict(self): return self.__dict__.copy()
