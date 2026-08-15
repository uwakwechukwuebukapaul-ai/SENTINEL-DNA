"""Immutable observed response outcome interpretation."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class ResponseOutcomes:
    tenant_id:str; outcomes_id:str; outcome_state:str="unknown"; observed_signals:tuple=(); temporal_interpretation:str="Insufficient evidence for outcome interpretation."; evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
