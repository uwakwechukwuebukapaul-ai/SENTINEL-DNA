from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class ThreatIndicator:
    organization_id: str; indicator_type: str; value: str; source: str; confidence: float = 0; severity: str = "MEDIUM"; first_seen: str = field(default_factory=now); last_seen: str = field(default_factory=now); tags: list[str] = field(default_factory=list); mitre_mapping: list[str] = field(default_factory=list); status: str = "ACTIVE"; id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now); updated_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class ThreatActor:
    organization_id: str; name: str; aliases: list[str] = field(default_factory=list); description: str = ""; motivation: str = ""; origin: str = ""; target_sectors: list[str] = field(default_factory=list); techniques: list[str] = field(default_factory=list); campaigns: list[str] = field(default_factory=list); id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class ThreatCampaign:
    organization_id: str; name: str; description: str; actor: str; target_sectors: list[str] = field(default_factory=list); techniques: list[str] = field(default_factory=list); indicators: list[str] = field(default_factory=list); severity: str = "HIGH"; first_seen: str = field(default_factory=now); last_seen: str = field(default_factory=now); status: str = "ACTIVE"; id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
