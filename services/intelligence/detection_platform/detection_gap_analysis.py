from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class DetectionGapAnalysis:
 tenant_id:str; analysis_id:str; missing_coverage_areas:tuple=(); improvement_opportunities:tuple=(); telemetry_dependencies:tuple=(); analyst_review_priorities:tuple=(); evidence_strength:str="insufficient_data"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
