from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class Organization:
    name: str; subscription_tier: str = "trial"; status: str = "active"; organization_id: str = None; created_at: str = None
    def __post_init__(self): self.organization_id = self.organization_id or str(uuid4()); self.created_at = self.created_at or now()
    def public(self): return asdict(self)
