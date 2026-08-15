"""Deterministic, tenant-scoped organizational learning observations."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class OrganizationalLearning:
    tenant_id: str
    organizational_learning_id: str
    pattern_type: str
    classification: str
    title: str
    description: str
    confidence: float | None
    uncertainty: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    contributing_investigation_ids: list = field(default_factory=list)
    contributing_feedback_ids: list = field(default_factory=list)
    contributing_learning_ids: list = field(default_factory=list)
    contributing_effectiveness_ids: list = field(default_factory=list)
    recommended_team_focus: str = ""
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)


def stable_organizational_learning_id(tenant_id, pattern_type, classification):
    return sha256(f"{tenant_id}|{pattern_type}|{classification}|organizational-learning".encode()).hexdigest()[:24]
