from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class BusinessAsset:
    asset_id:str; tenant_id:str; name:str; asset_type:str; business_unit:str=""; criticality:str="medium"; business_value:float=0.0; confidentiality:float=0.0; integrity:float=0.0; availability:float=0.0; regulatory_impact:float=0.0; revenue_impact:float=0.0; operational_impact:float=0.0; metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class ExecutiveRiskAssessment:
    assessment_id:str; tenant_id:str; overall_risk:float; risk_level:str; affected_assets:int=0; business_impact:float=0.0; confidence:float=0.0; created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class BusinessRiskFinding:
    finding_id:str=field(default_factory=lambda:str(uuid4())); tenant_id:str=""; asset_id:str=""; category:str="business_impact"; severity:str="medium"; explanation:str=""; recommendation:str=""; requires_human_review:bool=True; created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
