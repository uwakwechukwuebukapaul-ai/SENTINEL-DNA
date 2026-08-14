from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
@dataclass
class SecurityMemoryEntry:
    organization_id:str; incident_type:str; attack_pattern:str; decision:str; outcome:str; confidence:float; created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); id:str=field(default_factory=lambda:str(uuid4()))
    def public(self): return asdict(self)
class SecurityMemoryRepository:
    def __init__(self): self.entries=[]
    def add(self, **kwargs): x=SecurityMemoryEntry(**kwargs); self.entries.append(x); return x
    def scoped(self, org): return [x for x in self.entries if x.organization_id==org]
