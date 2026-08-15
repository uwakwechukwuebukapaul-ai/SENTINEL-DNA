"""Immutable cross-dimension risk coordination context."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class StrategicRiskCoordination:
    tenant_id:str; coordination_id:str; posture:str="insufficient_history"; risk_clusters:tuple=(); shared_dimensions:tuple=(); converging_risks:tuple=(); related_warnings:tuple=(); related_blockers:tuple=(); related_opportunities:tuple=(); coordination_themes:tuple=(); priority_review_areas:tuple=(); evidence_gaps:tuple=(); confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); contributing_references:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
