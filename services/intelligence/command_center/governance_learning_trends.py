from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class GovernanceLearningTrends:
    tenant_id:str; trends_id:str; learning_maturity_trend:str="insufficient_history"; recurring_themes:tuple=(); intervention_lessons:tuple=(); effectiveness_trend:str="insufficient_outcomes"; evidence_maturity_trend:str="insufficient_evidence"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
