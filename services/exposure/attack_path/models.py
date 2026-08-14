from dataclasses import asdict, dataclass, field
from uuid import uuid4

@dataclass
class AttackPath:
    organization_id: str; nodes: list[dict]; techniques: list[str]; risk: float; id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
