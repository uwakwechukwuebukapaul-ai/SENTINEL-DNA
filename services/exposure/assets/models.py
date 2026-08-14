from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

def now(): return datetime.now(timezone.utc).isoformat()

@dataclass
class Asset:
    organization_id: str
    hostname: str
    ip_address: str = ""
    asset_type: str = "SERVER"
    owner: str = ""
    criticality: str = "MEDIUM"
    environment: str = "production"
    last_seen: str = field(default_factory=now)
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    def public(self): return asdict(self)
