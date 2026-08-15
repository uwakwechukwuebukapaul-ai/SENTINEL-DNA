"""Immutable executive review priority; not an escalation command."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class InterventionPriority:
    tenant_id:str; priority_id:str; priority:str="P4_INFORMATIONAL"; rationale:tuple=(); supporting_signals:tuple=(); evidence_gaps:tuple=(); recommended_review_scope:tuple=(); organizational_focus:tuple=(); temporal_context:str="unavailable"; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
