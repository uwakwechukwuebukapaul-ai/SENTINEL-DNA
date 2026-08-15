"""Immutable warning lifecycle interpretation."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class EscalationLifecycle:
    tenant_id:str; lifecycle_id:str; lifecycle_state:str="insufficient_history"; previous_observable_state:str|None=None; transition_interpretation:str="No historical transition is available."; direction:str="unavailable"; persistence_interpretation:str="insufficient_history"; evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
