from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class SecuritySignal:
 organization_id:str; source:str; signal_type:str; severity:str; entity:str; entity_type:str; timestamp:str; metadata:dict=field(default_factory=dict); confidence:float=.8; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
@dataclass
class XDRIncident:
 organization_id:str; title:str; description:str; severity:str; risk_score:float; confidence:float; status:str="OPEN"; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now); updated_at:str=field(default_factory=now); signals:list=field(default_factory=list); story:dict=field(default_factory=dict)
 def public(self): return asdict(self)
@dataclass
class AttackStory:
 organization_id:str; incident_id:str; summary:str; attacker_goal:str; attack_stage:str; confidence:float; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
