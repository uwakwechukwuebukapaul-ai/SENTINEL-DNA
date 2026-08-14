from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class SOCTask:
 organization_id:str; task_type:str; priority:str="P3"; assigned_agent:str=""; status:str="CREATED"; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now); completed_at:str=""
 def public(self): return asdict(self)
@dataclass
class AgentProfile:
 organization_id:str; agent_name:str; capabilities:list=field(default_factory=list); availability:str="AVAILABLE"; performance_score:float=0; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
@dataclass
class SOCDecision:
 organization_id:str; decision_type:str; reasoning:str; confidence:float; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
