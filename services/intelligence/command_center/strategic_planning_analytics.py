"""Immutable longitudinal planning analytics contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
def stable_analytics_id(tenant_id,kind,*parts): return sha256(json.dumps([tenant_id,kind,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class StrategicPriorityLifecycle:
    tenant_id:str; stable_id:str; priority_id:str; title:str; dimension:str|None; classification:str; status:str; observation_count:int; recurrence_count:int; first_observed_at:str|None; last_observed_at:str|None; confidence:str|float|None; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); contributing_references:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class StrategicDecisionEffectiveness:
    tenant_id:str; stable_id:str; priority_id:str; classification:str; interpretation:str; score:int|None; confidence:str|float|None; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); advisory_only:bool=True
    def to_dict(self): return asdict(self)
