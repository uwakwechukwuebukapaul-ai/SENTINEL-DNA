"""Immutable analytical warning escalation records."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class WarningEscalation:
    tenant_id:str; escalation_id:str; warning_id:str|None=None; category:str="governance"; previous_state:str="unavailable"; current_state:str="unavailable"; transition:str="insufficient_history"; severity:str="informational"; temporal_context:str="unavailable"; evidence:tuple=(); confidence:str|float|None=None; uncertainty:tuple=(); contributing_references:tuple=(); organizational_dimension:str|None=None; advisory_recommendation:str="Review the analytical condition; no operational escalation is performed."; advisory_only:bool=True
    def to_dict(self): return asdict(self)
