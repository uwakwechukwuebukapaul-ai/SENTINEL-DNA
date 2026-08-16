from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class HuntingIntelligence:
 tenant_id:str; intelligence_id:str; current_hunting_posture:str="insufficient_history"; available_hunting_coverage:str="insufficient_data"; evidence_confidence:str="insufficient_data"; readiness_state:str="insufficient_history"; evidence_references:tuple=(); uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class HuntPrioritization:
 tenant_id:str; prioritization_id:str; priority_classification:str="insufficient_data"; supporting_evidence:tuple=(); confidence:str="insufficient_data"; reasoning_metadata:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class HuntEffectiveness:
 tenant_id:str; effectiveness_id:str; historical_effectiveness_indicators:tuple=(); outcome_associations:tuple=(); trend_interpretation:str="insufficient_history"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class HuntGapAnalysis:
 tenant_id:str; analysis_id:str; coverage_gaps:tuple=(); visibility_gaps:tuple=(); maturity_gaps:tuple=(); improvement_opportunities:tuple=(); evidence_strength:str="insufficient_data"; advisory_only:bool=True
 def to_dict(self):return asdict(self)
