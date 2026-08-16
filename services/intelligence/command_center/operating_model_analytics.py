from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class OperatingModelAnalytics:
 tenant_id:str; analytics_id:str; intelligence_operating_model_trends:str="insufficient_history"; capability_maturity_progression:str="insufficient_history"; adoption_indicators:tuple=(); continuous_improvement_observations:tuple=(); evidence_strength:str="insufficient_evidence"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
