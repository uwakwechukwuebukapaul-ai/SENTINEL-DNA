"""Immutable executive evidence-traceability contract."""
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ExecutiveLearningDrillDown:
    tenant_id: str
    signal_id: str
    signal: dict
    trend: dict | None = None
    organizational_dimensions: list = field(default_factory=list)
    learning: list = field(default_factory=list)
    effectiveness: list = field(default_factory=list)
    feedback: list = field(default_factory=list)
    references: list = field(default_factory=list)
    interpretation: str = ""
    recommended_focus: str = ""
    confidence: float | None = None
    uncertainty: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
