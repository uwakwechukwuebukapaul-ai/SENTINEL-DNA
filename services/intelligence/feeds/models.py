from dataclasses import dataclass, asdict
from uuid import uuid4
@dataclass
class ThreatFeed:
    organization_id: str; name: str; provider: str; feed_type: str; status: str = "configured"; last_sync: str | None = None; indicator_count: int = 0; id: str = None
    def __post_init__(self): self.id = self.id or str(uuid4())
    def public(self): return asdict(self)
