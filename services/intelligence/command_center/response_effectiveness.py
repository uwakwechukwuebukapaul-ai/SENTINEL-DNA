from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class ResponseEffectiveness:
    tenant_id:str; effectiveness_id:str; alignment:str="insufficient_evidence"; effectiveness_assessment:str="insufficient evidence for effectiveness assessment"; expected_measurement_signals:tuple=(); observed_progress_signals:tuple=(); evidence_sufficiency:str="insufficient_evidence"; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
