"""Immutable portfolio early-warning result."""
from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class PortfolioEarlyWarning:
    tenant_id:str; warning_id:str; warning_state:str="insufficient_history"; signals:tuple=(); risk_convergence:tuple=(); governance_deterioration:tuple=(); readiness_deterioration:tuple=(); recurring_blockers:tuple=(); evidence_limitations:tuple=(); organizational_dimensions:tuple=(); recommendations:tuple=(); provenance:tuple=(); uncertainty:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
