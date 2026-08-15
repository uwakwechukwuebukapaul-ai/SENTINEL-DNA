"""Immutable executive governance signals."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
def stable_governance_signal_id(tenant_id, *parts): return sha256(json.dumps([tenant_id,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class GovernanceSignal:
    tenant_id:str; signal_id:str; category:str; severity:str; title:str; summary:str; evidence:tuple=(); confidence:str|float|None=None; uncertainty:tuple=(); references:tuple=(); provenance:tuple=(); organizational_dimension:str|None=None; status:str="active"; advisory_only:bool=True
    def to_dict(self): return asdict(self)
