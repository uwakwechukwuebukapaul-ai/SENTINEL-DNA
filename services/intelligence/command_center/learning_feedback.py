"""Deterministic, advisory feedback observations for analyst learning."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class AnalystLearningFeedback:
    tenant_id: str
    feedback_id: str
    learning_type: str
    state: str
    what_changed: str
    why_it_changed: str
    effectiveness_state: str
    confidence: float | None
    uncertainty: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    contributing_feedback_ids: list = field(default_factory=list)
    contributing_investigation_ids: list = field(default_factory=list)
    contributing_learning_ids: list = field(default_factory=list)
    recommended_analyst_focus: str = ""
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)


def stable_learning_feedback_id(tenant_id, learning_type, state):
    return sha256(f"{tenant_id}|{learning_type}|{state}|feedback".encode()).hexdigest()[:24]
