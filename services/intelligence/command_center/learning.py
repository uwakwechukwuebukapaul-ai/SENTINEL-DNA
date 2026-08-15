"""Deterministic analyst learning observations over quality intelligence."""
from dataclasses import dataclass, asdict, field
from hashlib import sha256
@dataclass(frozen=True)
class AnalystInvestigationLearning:
    tenant_id: str; learning_id: str; learning_type: str; title: str; description: str; severity: str
    investigation_count: int; feedback_count: int; quality_signal_count: int; confidence: float | None = None
    uncertainty: list = field(default_factory=list); provenance: dict = field(default_factory=dict)
    contributing_feedback_ids: list = field(default_factory=list); contributing_investigation_ids: list = field(default_factory=list)
    contributing_attention_ids: list = field(default_factory=list); recommended_analyst_focus: str = ""; human_review_required: bool = True
    def to_dict(self): return asdict(self)
def stable_learning_id(tenant_id, learning_type): return sha256(f"{tenant_id}|{learning_type}".encode()).hexdigest()[:24]
