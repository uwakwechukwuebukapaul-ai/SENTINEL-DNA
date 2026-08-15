"""Deterministic analyst-facing interpretation of quality trends."""
from dataclasses import dataclass, asdict, field
@dataclass(frozen=True)
class QualityAttentionItem:
    attention_id: str; category: str; priority: str; reason: str; supporting_references: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict); confidence: float | None = None; uncertainty: list = field(default_factory=list); requires_human_review: bool = True
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class AnalystQualityIntelligence:
    tenant_id: str; state: str; trend_direction: str; investigation_count: int; feedback_count: int; quality_signal_count: int
    agreement_count: int; disagreement_count: int; unresolved_count: int; human_review_count: int; evidence_insufficient_count: int
    average_confidence: float | None = None; uncertainty: list = field(default_factory=list); attention: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict); contributing_feedback_ids: list = field(default_factory=list); contributing_investigation_ids: list = field(default_factory=list)
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
