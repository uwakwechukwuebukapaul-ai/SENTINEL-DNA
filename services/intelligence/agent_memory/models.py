from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from typing import Any
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class AgentExperience:
 experience_id:str; tenant_id:str; agent_id:str; case_id:str; task_type:str; outcome:dict[str,Any]=field(default_factory=dict); confidence:float=0.; created_at:str=field(default_factory=now); synthetic_only:bool=True
 def to_dict(self): return asdict(self)
@dataclass
class AgentMessage:
 message_id:str; tenant_id:str; sender:str; recipient:str; message_type:str; payload:dict[str,Any]=field(default_factory=dict); created_at:str=field(default_factory=now)
 def to_dict(self): return asdict(self)
@dataclass
class CollaborationContext:
 case_id:str; tenant_id:str; active_agents:list[str]=field(default_factory=list); messages:list[AgentMessage]=field(default_factory=list); shared_findings:list[dict[str,Any]]=field(default_factory=list)
 def to_dict(self): d=asdict(self); d["messages"]=[m.to_dict() for m in self.messages]; return d
@dataclass
class AnalystFeedback:
 feedback_id:str; tenant_id:str; agent_id:str; case_id:str; rating:int; comment:str=""; created_at:str=field(default_factory=now)
 def to_dict(self): return asdict(self)
