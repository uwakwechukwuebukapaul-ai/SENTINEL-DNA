"""Immutable forward-looking portfolio projection contracts."""
from dataclasses import asdict,dataclass,field
from hashlib import sha256
import json
def stable_forecast_id(tenant_id,kind,*parts): return sha256(json.dumps([tenant_id,kind,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class PortfolioForecastSignal:
    tenant_id:str; signal_id:str; title:str; signal_type:str; direction:str; horizon:str; dimension:str|None; projection:str; score:float|None; confidence:str|float|None; evidence_strength:str; uncertainty:tuple=(); provenance:tuple=(); contributing_references:tuple=(); evidence_type:str="forecast"; advisory_only:bool=True
    def to_dict(self): return asdict(self)
