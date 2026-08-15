from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class EscalationMonitoring:
    tenant_id:str; monitoring_id:str; lifecycle_distribution:dict=None; escalation_trend:str="insufficient_history"; recovery_trend:str="insufficient_history"; unresolved_signals:tuple=(); sustainability:str="insufficient_history"; stability:str="insufficient_history"; evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
