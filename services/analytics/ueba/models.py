from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class UserBehaviorProfile:
    organization_id: str; user_id: str; normal_login_hours: list = field(default_factory=list); known_locations: list = field(default_factory=list); known_devices: list = field(default_factory=list); known_applications: list = field(default_factory=list); normal_activity_volume: float = 0; normal_privileges: list = field(default_factory=list); risk_score: float = 0; id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now); updated_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class EntityBehaviorProfile:
    organization_id: str; entity_id: str; entity_type: str; baseline_behavior: dict = field(default_factory=dict); risk_score: float = 0; last_activity: str = ""; id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class BehaviorAnomaly:
    organization_id: str; entity_id: str; anomaly_type: str; description: str; risk_score: float; confidence: float; mitre_mapping: list = field(default_factory=list); id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class RiskScore:
    organization_id: str; entity_id: str; score: float; severity: str; signals: list = field(default_factory=list)
    def public(self): return asdict(self)
