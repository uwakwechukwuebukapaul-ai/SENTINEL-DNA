"""Immutable strategic planning and decision-history contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json

def stable_planning_id(tenant_id, kind, *parts): return sha256(json.dumps([tenant_id,kind,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class StrategicPlanningPriority:
    tenant_id:str; stable_id:str; classification:str; title:str; dimension:str|None; priority:str; rationale:str; evidence_strength:str; confidence:str|float|None; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); contributing_references:tuple=(); strategic_relevance:str=""; recommendation:str=""; advisory_only:bool=True
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class StrategicPlanningPosture:
    planning_status:str; strategic_posture:str; highest_priority_area:str|None; strongest_dimension:str|None; weakest_dimension:str|None; recurring_priorities:tuple; sustained_priorities:tuple; unresolved_priorities:tuple; resolved_priorities:tuple; reversals:tuple; emerging_themes:tuple; historical_evidence_quality:str; confidence:str|float|None; uncertainty:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
