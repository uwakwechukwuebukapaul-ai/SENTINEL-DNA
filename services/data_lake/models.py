from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

def now(): return datetime.now(timezone.utc).isoformat()

@dataclass
class SecurityEventRecord:
    organization_id: str
    timestamp: str
    source: str
    event_type: str
    severity: str = "INFO"
    raw_event: dict = field(default_factory=dict)
    normalized_event: dict = field(default_factory=dict)
    mitre_mapping: list[str] = field(default_factory=list)
    asset_id: str = ""
    user_id: str = ""
    ioc_matches: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    stored_at: str = field(default_factory=now)
    def public(self): return asdict(self)
