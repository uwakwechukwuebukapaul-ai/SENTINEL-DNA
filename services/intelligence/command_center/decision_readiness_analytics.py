"""Immutable longitudinal decision-readiness analytics."""
from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class DecisionReadinessAnalytics:
    tenant_id: str; analytics_id: str; readiness_trajectory: str="insufficient_history"; state_transitions: tuple=(); recurring_blockers: tuple=(); improvement_patterns: tuple=(); regression_patterns: tuple=(); risk_convergence: tuple=(); opportunity_convergence: tuple=(); organizational_dimensions: tuple=(); evidence_limitations: tuple=(); confidence: str|float|None=None; uncertainty: tuple=(); provenance: tuple=(); history_status: str="insufficient_history"; advisory_only: bool=True
    def to_dict(self): return asdict(self)
