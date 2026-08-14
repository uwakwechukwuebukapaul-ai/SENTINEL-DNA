from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
@dataclass
class GovernancePolicy:
    policy_id: str; tenant_id: str; name: str; category: str; description: str; rules: dict[str,Any]=field(default_factory=dict); enabled: bool=True; created_at: str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); updated_at: str=""
    def to_dict(self): return asdict(self)
@dataclass
class PolicyDecision:
    allowed: bool; reason: str; policy_id: str|None=None; metadata: dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return asdict(self)
