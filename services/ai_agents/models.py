from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class SOCAgent:
    organization_id:str; name:str; agent_type:str; capabilities:list=field(default_factory=list); status:str="IDLE"; confidence:float=0; last_execution:str=""; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class AgentMemory:
    organization_id:str; kind:str; content:dict; confidence:float=0; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
    def public(self): return asdict(self)
