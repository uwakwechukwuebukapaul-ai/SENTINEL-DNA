"""Immutable governance learning signals."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class GovernanceLearning:
    tenant_id:str; learning_id:str; recurring_patterns:tuple=(); lessons_learned:tuple=(); evidence_strength:str="insufficient_evidence"; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
