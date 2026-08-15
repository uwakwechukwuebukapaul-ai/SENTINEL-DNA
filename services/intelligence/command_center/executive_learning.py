"""Deterministic executive learning intelligence contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class ExecutiveLearningSignal:
    tenant_id: str
    executive_signal_id: str
    signal_type: str
    title: str
    summary: str
    classification: str
    priority: str
    severity: str
    confidence: float | None
    uncertainty: list = field(default_factory=list)
    evidence_strength: str = "insufficient"
    trend_direction: str = "unknown"
    organizational_scope: str | None = None
    team_focus: str | None = None
    learning_focus: str = ""
    effectiveness_summary: str = ""
    contributing_references: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    temporal_context: dict = field(default_factory=dict)
    recommended_focus: str = ""
    relevance_score: float = 0.0
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ExecutiveLearningSummary:
    tenant_id: str
    overall_posture: str
    signal_count: int
    critical_gap_count: int
    persistent_gap_count: int
    degrading_count: int
    improving_count: int
    emerging_count: int
    resolved_count: int
    confidence: float | None
    evidence_quality: str
    dominant_organizational_focus: str
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)


def stable_executive_signal_id(tenant_id, signal_type, organizational_scope=None):
    return sha256(f"{tenant_id}|{signal_type}|{organizational_scope or 'unavailable'}|executive-learning".encode()).hexdigest()[:24]
