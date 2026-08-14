from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class SecurityPosture:
 organization_id:str; overall_score:float; risk_score:float; maturity_level:str; strengths:list=field(default_factory=list); weaknesses:list=field(default_factory=list); id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class RiskAssessment:
 organization_id:str; risk_category:str; severity:str; business_impact:str; likelihood:float; recommendation:str; confidence:float; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
@dataclass
class SecurityRecommendation:
 organization_id:str; priority:str; recommendation:str; expected_risk_reduction:float; estimated_effort:str; status:str="OPEN"; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
