from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class ThreatActor:
    name: str; motivation: str; target: str; techniques: list[str] = field(default_factory=list); campaign_history: list[str] = field(default_factory=list); id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
@dataclass
class AttackStage:
    name: str; technique_id: str; tactic: str; description: str; order: int; id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
@dataclass
class AttackCampaign:
    name: str; actor: ThreatActor; target: str; stages: list[AttackStage]; id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now); status: str = "draft"
    def public(self):
        value = asdict(self); value["actor"] = self.actor.public(); return value
