from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class InterventionGovernanceTrends:
    tenant_id:str; trends_id:str; governance_posture_trend:str="insufficient_history"; readiness_trend:str="insufficient_history"; lifecycle_trend:str="insufficient_history"; risk_coordination_trend:str="insufficient_history"; evidence_maturity:str="insufficient_history"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
