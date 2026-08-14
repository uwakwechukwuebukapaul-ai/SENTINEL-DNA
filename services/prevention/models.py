from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class PreventionRecommendation:
 organization_id:str; incident_id:str; asset_id:str; risk_score:float; threat_description:str; recommended_actions:list; confidence:float; status:str="CREATED"; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class SecurityAction:
 organization_id:str; action_type:str; target:str; reason:str; approval_required:bool=True; execution_status:str="PENDING"; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class PreventionOutcome:
 organization_id:str; action_id:str; result:str; effectiveness_score:float; lessons_learned:str; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
