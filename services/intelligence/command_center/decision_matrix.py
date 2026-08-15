"""Immutable multi-scenario comparison contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json

def stable_matrix_id(tenant_id, selections): return sha256(json.dumps([tenant_id,selections],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class ScenarioComparison:
    tenant_id:str; comparison_id:str; scenario_id:str; scenario_type:str; title:str; strategic_area:str; target_dimension:str|None; classification:str; baseline_score:float|None; scenario_score:float|None; score_delta:float|None; strategic_priority:str; confidence:str; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); contributing_references:tuple=(); expected_focus:str=""; trade_offs:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class DecisionMatrix:
    tenant_id:str; matrix_id:str; baseline_context:dict; scenarios:tuple; ranked_scenarios:tuple; strategic_recommendation:dict; trade_off_summary:dict; evidence_summary:dict; confidence:str; evidence_strength:str; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
