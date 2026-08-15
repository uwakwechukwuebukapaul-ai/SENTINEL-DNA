from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class GovernanceLearningTrendsAnalytics:
    tenant_id:str; analytics_id:str; trend:str="insufficient_history"; maturity_movement:str="insufficient_history"; recurring_themes:tuple=(); lessons:tuple=(); evidence_strength:str="insufficient_evidence"; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
