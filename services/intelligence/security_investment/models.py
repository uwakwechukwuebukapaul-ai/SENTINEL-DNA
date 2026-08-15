from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class SecurityImprovementOpportunity:
    opportunity_id:str; tenant_id:str; title:str; category:str; affected_assets:list=field(default_factory=list); affected_business_units:list=field(default_factory=list); related_risks:list=field(default_factory=list); current_control_effectiveness:float=0.0; estimated_cost:float=0.0; metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class InvestmentPriority:
    priority_id:str; tenant_id:str; opportunity_id:str; priority_score:float; rank:int=0; rationale:str=""; requires_human_review:bool=True; created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class RiskReductionEstimate:
    estimate_id:str=field(default_factory=lambda:str(uuid4())); tenant_id:str=""; opportunity_id:str=""; current_risk:float=0.0; projected_risk:float=0.0; reduction:float=0.0; confidence:float=0.0
    def to_dict(self): return asdict(self)
