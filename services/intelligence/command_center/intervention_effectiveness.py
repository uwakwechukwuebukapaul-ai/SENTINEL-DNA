"""Immutable intervention effectiveness analytics."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class InterventionEffectiveness:
    tenant_id:str; effectiveness_id:str; assessment:str="insufficient_history"; readiness_alignment:str="insufficient_evidence"; effectiveness_indicators:tuple=(); temporal_association:str="insufficient evidence for effectiveness assessment"; evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
