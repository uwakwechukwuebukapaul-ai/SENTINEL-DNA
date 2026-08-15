"""Immutable aggregate analytics for forecast policy review."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
def stable_policy_analytics_id(tenant_id, *parts): return sha256(json.dumps([tenant_id,*parts],sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()[:24]
@dataclass(frozen=True)
class ForecastPolicyAnalytics:
    tenant_id: str; analytics_id: str; policy_review_references: tuple=(); forecast_references: tuple=(); governance_references: tuple=(); current_policy_posture: str="insufficient_history"; historical_policy_posture: str="insufficient_history"; readiness_distribution: dict=None; blocker_distribution: dict=None; reliability_distribution: dict=None; calibration_distribution: dict=None; drift_distribution: dict=None; risk_monitoring_distribution: dict=None; confidence: str|float|None=None; evidence_strength: str|None=None; uncertainty: tuple=(); provenance: tuple=(); contributing_references: tuple=(); temporal_coverage: str="unavailable"; history_status: str="insufficient_history"; advisory_only: bool=True
    def to_dict(self): return asdict(self)
