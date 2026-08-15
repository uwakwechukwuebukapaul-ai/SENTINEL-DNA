"""Immutable cross-dimension executive portfolio contracts."""
from dataclasses import asdict,dataclass,field
from hashlib import sha256
import json
def stable_command_center_id(tenant_id,kind,*parts): return sha256(json.dumps([tenant_id,kind,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class PortfolioCommandSignal:
    tenant_id:str; signal_id:str; title:str; dimension:str|None; state:str; category:str; priority:str; score:float|None; confidence:str|float|None; evidence_strength:str; uncertainty:tuple=(); provenance:dict=field(default_factory=dict); contributing_references:tuple=(); evidence_type:str="derived"; recommendation:str=""; advisory_only:bool=True
    def to_dict(self): return asdict(self)
