"""Immutable forecast policy-review contracts."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

def stable_policy_review_id(tenant_id, kind, *parts):
    return sha256(json.dumps([tenant_id, kind, *parts], sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:24]

@dataclass(frozen=True)
class ForecastPolicyReview:
    tenant_id: str
    review_id: str
    forecast_reference: str | None
    governance_reference: str | None
    portfolio_reference: str | None
    review_status: str
    policy_readiness: str
    reliability_state: str | None
    calibration_state: str | None
    drift_state: str | None
    risk_monitoring_state: str | None
    evidence_strength: str | None
    confidence: str | float | None
    uncertainty: tuple = ()
    provenance: tuple = ()
    contributing_references: tuple = ()
    review_reasons: tuple = ()
    policy_constraints: tuple = ()
    advisory_recommendations: tuple = ()
    classification: str = "derived"
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
