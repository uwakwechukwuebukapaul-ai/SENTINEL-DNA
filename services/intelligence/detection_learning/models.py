from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

class AnalystVerdict(str, Enum):
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    BENIGN = "benign"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class DetectionFeedback:
    detection_id: str
    analyst_verdict: AnalystVerdict | str
    true_positive: bool | None = None
    false_positive: bool | None = None
    severity_adjustment: int | float | None = None
    tuning_notes: str = ""
    analyst_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None

    def __post_init__(self) -> None:
        if not self.detection_id.strip():
            raise ValueError("detection_id must not be empty")
        verdict = self.analyst_verdict.value if isinstance(self.analyst_verdict, AnalystVerdict) else str(self.analyst_verdict)
        if self.true_positive is None and self.false_positive is None:
            object.__setattr__(self, "true_positive", verdict == AnalystVerdict.TRUE_POSITIVE.value)
            object.__setattr__(self, "false_positive", verdict in (AnalystVerdict.FALSE_POSITIVE.value, AnalystVerdict.BENIGN.value))

@dataclass(frozen=True)
class DetectionMetrics:
    detection_id: str
    total_feedback: int
    true_positives: int
    false_positives: int
    precision: float
    false_positive_rate: float
    effectiveness_score: float
    confidence: float

@dataclass(frozen=True)
class Recommendation:
    detection_id: str
    kind: str
    rationale: str
    priority: str = "medium"
    actions: tuple[str, ...] = ()
    requires_human_approval: bool = True

@dataclass(frozen=True)
class LearningContext:
    metrics: DetectionMetrics | None = None
    recommendations: tuple[Recommendation, ...] = ()
    memory_refs: tuple[str, ...] = ()
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {"metrics": self.metrics.__dict__ if self.metrics else None, "recommendations": [r.__dict__ for r in self.recommendations], "memory_refs": list(self.memory_refs), "generated_at": self.generated_at.isoformat()}
