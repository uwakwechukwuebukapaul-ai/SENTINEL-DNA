"""Immutable strategic portfolio contracts."""
from dataclasses import asdict,dataclass,field
from hashlib import sha256
import json
def stable_portfolio_id(tenant_id,kind,*parts): return sha256(json.dumps([tenant_id,kind,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class StrategicPortfolioSignal:
    tenant_id:str; signal_id:str; priority_id:str; dimension:str|None; lifecycle_state:str; effectiveness_state:str; portfolio_status:str; priority:str; score:float|None; confidence:str|float|None; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); contributing_references:tuple=(); observed_references:tuple=(); derived_references:tuple=(); modeled_references:tuple=(); recommendation:str=""; advisory_only:bool=True
    def to_dict(self): return asdict(self)
