from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class ValidationScenario:
 organization_id:str; name:str; description:str; attack_type:str; mitre_techniques:list=field(default_factory=list); severity:str="HIGH"; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class ValidationExecution:
 organization_id:str; scenario_id:str; status:str="CREATED"; started_at:str=field(default_factory=now); completed_at:str=""; score:float=0; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
@dataclass
class ValidationResult:
 organization_id:str; execution_id:str; detection_score:float; investigation_score:float; prevention_score:float; automation_score:float; ai_score:float; overall_score:float; gaps:list=field(default_factory=list); recommendations:list=field(default_factory=list); id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
