"""Immutable executive strategic intelligence contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json

def stable_strategy_id(tenant_id, kind, *parts):
    return sha256(json.dumps([tenant_id,kind,*parts],sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()[:24]

@dataclass(frozen=True)
class StrategicSignal:
    tenant_id:str; signal_id:str; signal_type:str; title:str; description:str; priority:str; severity:str|None; strategic_area:str; organizational_dimension:str|None; current_state:str; trend:str; score:float|None; confidence:float|None; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); contributing_references:tuple=(); recommended_focus:str=""; advisory_only:bool=True
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ExecutivePosture:
    posture:str; posture_reason:str; current_maturity:str|None; maturity_score:float|None; maturity_trajectory:str; improvement_state:str; regression_state:str; sustainability_state:str; confidence:float|None; evidence_strength:str; uncertainty:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class StrategicScorecardItem:
    dimension:str; current_value:float|None; state:str; trend:str; confidence:float|None; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
