"""Immutable intervention-readiness analytics."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class InterventionReadiness:
    tenant_id:str; readiness_id:str; readiness_classification:str="insufficient_history"; governance_posture:str="insufficient_history"; lifecycle_state:str="insufficient_history"; response_priority:str="P4_INFORMATIONAL"; evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); blockers:tuple=(); recommendations:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
