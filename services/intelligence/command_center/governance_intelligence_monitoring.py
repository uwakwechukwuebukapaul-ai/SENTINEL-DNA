from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class GovernanceIntelligenceMonitoring:
 tenant_id:str; monitoring_id:str; governance_signal_monitoring:str="insufficient_history"; governance_readiness_trends:str="insufficient_history"; policy_alignment_observation:str="insufficient_evidence"; oversight_requirement_tracking:tuple=("human_review_required",); governance_intelligence_maturity:str="insufficient_history"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
