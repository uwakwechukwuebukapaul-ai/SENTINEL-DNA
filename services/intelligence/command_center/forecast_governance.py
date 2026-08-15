"""Immutable forecast governance contracts."""
from dataclasses import asdict,dataclass,field
from hashlib import sha256
import json
def stable_governance_id(tenant_id,kind,*parts): return sha256(json.dumps([tenant_id,kind,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class ForecastGovernanceSignal:
    tenant_id:str; stable_id:str; signal_type:str; severity:str; status:str; title:str; description:str; affected_dimension:str|None; supporting_references:tuple=(); confidence:str|float|None=None; evidence_strength:str="insufficient"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
