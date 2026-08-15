"""Immutable advisory strategic risk response planning."""
from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class RiskResponsePlanning:
    tenant_id:str; planning_id:str; strategic_risk:str|None=None; response_priority:str="P4_INFORMATIONAL"; response_objective:str="Review available evidence."; planning_consideration:str="No response is executed by this service."; expected_measurement_signal:str="Additional observed evidence and governance review."; evidence_requirements:tuple=(); governance_prerequisites:tuple=(); uncertainty:tuple=(); confidence:str|float|None=None; provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
