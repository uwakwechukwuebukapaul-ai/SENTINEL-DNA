"""Deterministic, advisory longitudinal learning effectiveness observations."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class AnalystLearningEffectiveness:
    tenant_id: str
    effectiveness_id: str
    learning_type: str
    classification: str
    effectiveness_score: float | None
    persistence: bool
    confidence: float | None = None
    uncertainty: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    contributing_feedback_ids: list = field(default_factory=list)
    contributing_investigation_ids: list = field(default_factory=list)
    contributing_learning_ids: list = field(default_factory=list)
    contributing_outcome_references: list = field(default_factory=list)
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)


def stable_effectiveness_id(tenant_id, learning_type):
    return sha256(f"{tenant_id}|{learning_type}|effectiveness".encode()).hexdigest()[:24]
