"""Deterministic aggregate quality observations over analyst feedback."""
from dataclasses import dataclass, asdict, field
@dataclass(frozen=True)
class AnalystQualityTrend:
    tenant_id: str
    investigation_count: int = 0
    feedback_count: int = 0
    quality_signal_count: int = 0
    agreement_count: int = 0
    disagreement_count: int = 0
    unresolved_investigation_count: int = 0
    human_review_required_count: int = 0
    evidence_insufficient_count: int = 0
    average_confidence: float | None = None
    uncertainty: list = field(default_factory=list)
    trend_direction: str = "insufficient_data"
    provenance: dict = field(default_factory=dict)
    contributing_feedback_ids: list = field(default_factory=list)
    contributing_investigation_ids: list = field(default_factory=list)
    contributing_outcome_references: list = field(default_factory=list)
    def to_dict(self): return asdict(self)
