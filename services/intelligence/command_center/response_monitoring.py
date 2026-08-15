from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class ResponseMonitoring:
    tenant_id:str; monitoring_id:str; trend:str="insufficient_history"; improvement_persistence:str="insufficient_history"; regression_indicators:tuple=(); stability_indicators:tuple=(); unresolved_areas:tuple=(); evidence_limitations:tuple=(); confidence:str|float|None=None; provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
