from dataclasses import asdict,dataclass
import hashlib
def stable_id(t,c,k):return f"{k}-{hashlib.sha256(f'{t}:{c}:{k}'.encode()).hexdigest()[:20]}"
@dataclass(frozen=True)
class LifecycleIntelligence:
 tenant_id:str;case_id:str;lifecycle_id:str;current_lifecycle_stage:str="intake";investigation_posture:str="insufficient_history";completion_indicators:tuple=();evidence_readiness:str="insufficient_data";uncertainty:tuple=();provenance:tuple=();confidence:str="insufficient_data";advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class InvestigationProgress:
 tenant_id:str;case_id:str;progress_id:str;progression_signals:tuple=();blocked_areas:tuple=();missing_evidence:tuple=();analyst_attention_areas:tuple=();confidence:str="insufficient_data";advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class InvestigationQuality:
 tenant_id:str;case_id:str;quality_id:str;evidence_coverage:str="insufficient_data";reasoning_completeness:str="insufficient_data";provenance_availability:str="insufficient_data";confidence_quality:str="insufficient_data";documentation_quality:str="insufficient_data";advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class AnalystWorkflow:
 tenant_id:str;case_id:str;workflow_id:str;workflow_observations:tuple=();friction_indicators:tuple=();suggested_improvements:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class InvestigationMetrics:
 tenant_id:str;metrics_id:str;aggregate_investigation_trends:tuple=();lifecycle_duration_interpretation:str="insufficient_history";recurring_investigation_patterns:tuple=();uncertainty:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
