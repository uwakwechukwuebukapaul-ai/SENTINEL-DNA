"""Immutable improvement-program analytics contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class ImprovementProgram:
    tenant_id: str; program_id: str; dimension: str; priority: str; status: str; progress_classification: str
    baseline_score: float | None; current_score: float | None; score_delta: float | None; target_score: float | None
    progress_percentage: float | None; trajectory: str; outcome_measurement: str; effectiveness: str
    confidence: float | None; evidence_strength: str; uncertainty: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict); contributing_references: list = field(default_factory=list)
    measurement_window: str = ""; baseline_period: str = ""; current_period: str = ""
    recommendation: str = ""; advisory_only: bool = True
    def to_dict(self): return asdict(self)


def stable_program_id(tenant_id, dimension): return sha256(f"{tenant_id}|{dimension}|improvement-program".encode()).hexdigest()[:24]
