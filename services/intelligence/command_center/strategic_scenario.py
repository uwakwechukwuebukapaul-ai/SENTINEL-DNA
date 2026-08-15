"""Immutable deterministic strategic scenario contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json

def stable_scenario_id(tenant_id, scenario_type, target_dimension, assumption):
    return sha256(json.dumps([tenant_id,scenario_type,target_dimension,assumption],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]

@dataclass(frozen=True)
class StrategicScenario:
    tenant_id:str; scenario_id:str; scenario_type:str; title:str; description:str; assumption:str; strategic_area:str; target_dimension:str|None; baseline_state:str; scenario_state:str; baseline_score:float|None; scenario_score:float|None; score_delta:float|None; baseline_trajectory:str; scenario_trajectory:str; classification:str; confidence:str; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); contributing_references:tuple=(); expected_focus:str=""; advisory_only:bool=True
    def to_dict(self): return asdict(self)
