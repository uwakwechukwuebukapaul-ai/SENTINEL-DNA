"""Immutable forecast evaluation contracts."""
from dataclasses import asdict,dataclass,field
from hashlib import sha256
import json
def stable_accuracy_id(tenant_id,forecast_id): return sha256(json.dumps([tenant_id,forecast_id],sort_keys=True,separators=(",",":")).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class ForecastEvaluation:
    tenant_id:str; evaluation_id:str; forecast_signal_id:str; forecast_direction:str; observed_direction:str|None; alignment:str; directional_accuracy:bool|None; forecast_score:float|None; observed_score:float|None; absolute_error:float|None; confidence:str|float|None; evidence_strength:str; uncertainty:tuple=(); provenance:tuple=(); evaluation_status:str="insufficient_evidence"; advisory_only:bool=True
    def to_dict(self): return asdict(self)
