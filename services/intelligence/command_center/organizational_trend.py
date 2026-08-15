"""Deterministic historical organizational trend contract."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class OrganizationalTrend:
    tenant_id: str
    trend_id: str
    trend_type: str
    title: str
    description: str
    classification: str
    direction: str
    priority: str
    confidence: float | None
    uncertainty: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    contributing_investigation_ids: list = field(default_factory=list)
    contributing_feedback_ids: list = field(default_factory=list)
    contributing_learning_ids: list = field(default_factory=list)
    contributing_effectiveness_ids: list = field(default_factory=list)
    observation_count: int = 0
    historical_span: str = ""
    first_observed: str | None = None
    last_observed: str | None = None
    previous_state: str | None = None
    current_state: str | None = None
    organizational_dimension: str = "unavailable"
    recommended_organizational_focus: str = ""
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)


def stable_organizational_trend_id(tenant_id, trend_type, dimension="unavailable"):
    return sha256(f"{tenant_id}|{trend_type}|{dimension}|organizational-trend".encode()).hexdigest()[:24]
