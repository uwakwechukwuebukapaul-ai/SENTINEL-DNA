from dataclasses import asdict,dataclass
import hashlib
def stable_id(t,c,k):return f"{k}-{hashlib.sha256(f'{t}:{c}:{k}'.encode()).hexdigest()[:20]}"
@dataclass(frozen=True)
class InvestigationIntelligence:
 tenant_id:str;case_id:str;intelligence_id:str;investigation_posture:str="insufficient_data";investigation_confidence:str="insufficient_data";evidence_completeness:str="insufficient_data";threat_interpretation:str="Insufficient evidence for threat interpretation; analyst review required.";analyst_guidance:tuple=();provenance:tuple=();evidence_references:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class EvidenceReasoning:
 tenant_id:str;case_id:str;reasoning_id:str;evidence_relationships:tuple=();supporting_indicators:tuple=();missing_evidence:tuple=();evidence_quality_interpretation:str="insufficient_data";uncertainty:tuple=();provenance:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class ThreatAssessment:
 tenant_id:str;case_id:str;assessment_id:str;threat_posture:str="insufficient_data";severity_interpretation:str="insufficient_data";confidence:str="insufficient_data";uncertainty_reasons:tuple=();provenance:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class InvestigationPlanning:
 tenant_id:str;case_id:str;plan_id:str;recommended_investigation_steps:tuple=();evidence_collection_priorities:tuple=();analyst_questions:tuple=();validation_suggestions:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
@dataclass(frozen=True)
class InvestigationSummary:
 tenant_id:str;case_id:str;summary_id:str;executive_summary:str;analyst_summary:str;evidence_summary:str;uncertainty_summary:str;recommended_actions:tuple=();provenance:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
