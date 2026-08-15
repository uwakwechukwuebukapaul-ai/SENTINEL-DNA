"""Immutable intervention governance review context."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class InterventionGovernance:
    tenant_id:str; governance_id:str; governance_posture:str="insufficient_history"; intervention_readiness:str="insufficient_history"; evidence_sufficiency:str="insufficient_evidence"; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); governance_blockers:tuple=(); intervention_considerations:tuple=(); executive_review_requirements:tuple=(); advisory_recommendations:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
