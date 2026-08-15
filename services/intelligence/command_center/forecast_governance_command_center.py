"""Immutable unified executive governance posture."""
from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ForecastGovernanceCommandCenter:
    tenant_id:str; command_center_id:str; governance_posture:str="insufficient_history"; readiness_posture:str="insufficient_history"; policy_posture:str="insufficient_history"; forecast_reliability:str|None=None; calibration_status:str|None=None; drift_status:str|None=None; risk_monitoring_status:str|None=None; early_warning_level:str="insufficient_history"; governance_blockers:tuple=(); decision_readiness_blockers:tuple=(); recurring_blockers:tuple=(); strategic_risks:tuple=(); strategic_opportunities:tuple=(); portfolio_health:str|None=None; trajectory:str="insufficient_history"; evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); history_status:str="insufficient_history"; decision_history_status:str="insufficient_decision_history"; temporal_coverage:str="unavailable"; contributing_references:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
