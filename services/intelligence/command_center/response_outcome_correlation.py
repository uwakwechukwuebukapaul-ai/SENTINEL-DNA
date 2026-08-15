from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class ResponseOutcomeCorrelation:
    tenant_id:str; correlation_id:str; relationship:str="insufficient_history"; candidates:tuple=(); relationship_strength:str="unavailable"; evidence_availability:str="insufficient_outcomes"; temporal_association:str="No causal relationship is claimed."; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
