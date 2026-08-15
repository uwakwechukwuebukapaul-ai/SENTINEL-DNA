from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class InterventionStrategyAnalytics:
    tenant_id:str; analytics_id:str; strategy_posture:str="insufficient_evidence"; strategy_patterns:tuple=(); effectiveness_patterns:tuple=(); response_alignment:str="insufficient_evidence"; governance_maturity_alignment:str="insufficient_evidence"; improvement_opportunities:tuple=(); uncertainty:tuple=(); confidence:str|float|None=None; provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
