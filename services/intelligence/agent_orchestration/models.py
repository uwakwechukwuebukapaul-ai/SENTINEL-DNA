from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from typing import Any
@dataclass
class SOCAgent:
 agent_id:str; name:str; agent_type:str; description:str=""; capabilities:list[str]=field(default_factory=list); status:str="available"; tenant_id:str="default"; version:str="1.0"
 def to_dict(self): return asdict(self)
@dataclass
class AgentTask:
 task_id:str; case_id:str; agent_id:str; task_type:str; input_context:dict[str,Any]=field(default_factory=dict); priority:int=50; status:str="queued"; result:Any=None; created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); completed_at:str|None=None
 def to_dict(self): return asdict(self)
@dataclass
class AgentExecutionSummary:
 completed_agents:list[str]=field(default_factory=list); failed_agents:list[str]=field(default_factory=list); pending_tasks:int=0; execution_time:float=0.0
 def to_dict(self): return asdict(self)
