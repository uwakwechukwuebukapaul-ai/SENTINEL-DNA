"""Immutable governance posture history analytics."""
from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class GovernancePostureAnalytics:
    tenant_id:str; analytics_id:str; trajectory:str="insufficient_history"; posture_transitions:tuple=(); blocker_persistence:tuple=(); warning_persistence:tuple=(); readiness_transitions:tuple=(); deterioration_patterns:tuple=(); recovery_patterns:tuple=(); evidence_limitations:tuple=(); confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); temporal_coverage:str="unavailable"; advisory_only:bool=True
    def to_dict(self): return asdict(self)
