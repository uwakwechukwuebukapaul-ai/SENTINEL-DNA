"""Immutable executive maturity reporting contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class MaturityReport:
    tenant_id: str
    report_id: str
    current_score: float | None
    previous_score: float | None
    score_delta: float | None
    current_level: str
    previous_level: str | None
    trajectory: str
    maturity_transition: str
    dimension_summaries: list = field(default_factory=list)
    strongest_dimensions: list = field(default_factory=list)
    weakest_dimensions: list = field(default_factory=list)
    improving_dimensions: list = field(default_factory=list)
    degrading_dimensions: list = field(default_factory=list)
    persistent_strengths: list = field(default_factory=list)
    persistent_weaknesses: list = field(default_factory=list)
    evidence_strength: str = "insufficient"
    confidence: float | None = None
    uncertainty: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    contributing_references: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    observation_count: int = 0
    temporal_span: str = ""
    interpretation: str = ""
    peer_benchmark_status: str = "unavailable"
    advisory_only: bool = True

    def to_dict(self): return asdict(self)


def stable_report_id(tenant_id):
    return sha256(f"{tenant_id}|executive-maturity-report".encode()).hexdigest()[:24]
