"""Immutable advisory decision-oversight contracts."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

def stable_oversight_id(tenant_id, *parts):
    return sha256(json.dumps([tenant_id, *parts], sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:24]

@dataclass(frozen=True)
class DecisionOversight:
    tenant_id: str
    oversight_id: str
    forecast_reference: str | None
    policy_review_reference: str | None
    portfolio_reference: str | None
    oversight_posture: str
    decision_readiness: str
    key_risks: tuple = ()
    key_opportunities: tuple = ()
    governance_blockers: tuple = ()
    evidence_requirements: tuple = ()
    uncertainty_considerations: tuple = ()
    scenario_references: tuple = ()
    decision_matrix_references: tuple = ()
    strategic_planning_references: tuple = ()
    recommendations: tuple = ()
    provenance: tuple = ()
    decision_history_status: str = "insufficient_decision_history"
    advisory_only: bool = True

    def to_dict(self): return asdict(self)
