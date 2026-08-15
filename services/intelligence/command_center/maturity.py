"""Internal, evidence-based organizational maturity contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class MaturityDimension:
    dimension_id: str
    display_name: str
    maturity_level: str
    score: float | None
    classification: str
    confidence: float | None
    evidence_strength: str
    uncertainty: list = field(default_factory=list)
    observation_count: int = 0
    temporal_span: str = ""
    contributing_references: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    advisory_only: bool = True

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class OrganizationalMaturity:
    tenant_id: str
    maturity_score: float | None
    maturity_level: str
    classification: str
    dimensions: list = field(default_factory=list)
    signals: list = field(default_factory=list)
    historical_baseline: float | None = None
    baseline_delta: float | None = None
    benchmark_status: str = "insufficient_history"
    trend: str = "insufficient_data"
    confidence: float | None = None
    evidence_strength: str = "insufficient"
    uncertainty: list = field(default_factory=list)
    observation_count: int = 0
    temporal_span: str = ""
    contributing_references: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    recommendations: list = field(default_factory=list)
    peer_benchmark_status: str = "unavailable"
    advisory_only: bool = True

    def to_dict(self):
        value = asdict(self); value["dimensions"] = [x.to_dict() if hasattr(x, "to_dict") else x for x in self.dimensions]; return value


def stable_maturity_id(tenant_id, dimension_id="overall"):
    return sha256(f"{tenant_id}|{dimension_id}|maturity".encode()).hexdigest()[:24]
