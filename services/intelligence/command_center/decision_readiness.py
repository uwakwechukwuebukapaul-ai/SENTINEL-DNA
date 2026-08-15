"""Immutable portfolio decision-readiness context."""
from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class DecisionReadiness:
    tenant_id: str; readiness_id: str; readiness_classification: str="insufficient_history"; policy_review_status: str="insufficient_history"; governance_status: str="insufficient_evidence"; reliability: str|None=None; calibration: str|None=None; drift: str|None=None; risk_monitoring: str|None=None; evidence_strength: str|None=None; confidence: str|float|None=None; uncertainty: tuple=(); governance_blockers: tuple=(); strategic_risks: tuple=(); strategic_opportunities: tuple=(); scenario_references: tuple=(); decision_matrix_references: tuple=(); planning_references: tuple=(); recommendations: tuple=(); provenance: tuple=(); decision_history_status: str="insufficient_decision_history"; advisory_only: bool=True
    def to_dict(self): return asdict(self)
