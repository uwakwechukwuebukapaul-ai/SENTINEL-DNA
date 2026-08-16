from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class DecisionIntelligenceAnalytics:
 tenant_id:str; analytics_id:str; decision_intelligence_readiness:str="insufficient_history"; evidence_completeness_monitoring:str="insufficient_evidence"; decision_context_quality:str="insufficient_history"; decision_lifecycle_analytics:str="insufficient_history"; strategic_decision_readiness:str="insufficient_history"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
