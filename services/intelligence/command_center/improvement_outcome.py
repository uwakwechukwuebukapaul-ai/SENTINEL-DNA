"""Immutable improvement outcome and executive progress contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class ImprovementProgramOutcome:
    tenant_id: str; program_id: str; dimension: str; priority: str; program_status: str; outcome_status: str; outcome_classification: str
    baseline_score: float | None; prior_score: float | None; current_score: float | None; target_score: float | None; score_delta: float | None; progress_percentage: float | None; improvement_velocity: str; trajectory: str; sustained: str; regression_detected: bool; effectiveness: str; outcome_strength: str; confidence: float | None; evidence_strength: str; uncertainty: list = field(default_factory=list); measurement_window: str = ""; baseline_period: str = ""; prior_period: str = ""; current_period: str = ""; provenance: dict = field(default_factory=dict); contributing_references: list = field(default_factory=list); recommendation: str = ""; advisory_only: bool = True
    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class ExecutiveImprovementProgress:
    tenant_id: str; total_programs: int; meaningful_improvements: int; sustained_improvements: int; partial_improvements: int; stable_programs: int; stalled_programs: int; regressions: int; degrading_programs: int; insufficient_data: int; overall_progress: float | None; overall_effectiveness: str; improvement_velocity: str; strongest_improvement: str | None; weakest_dimension: str | None; highest_priority_regression: str | None; sustainability_rate: float | None; executive_confidence: float | None; evidence_strength: str; uncertainty: list = field(default_factory=list); provenance: dict = field(default_factory=dict); recommendations: list = field(default_factory=list); advisory_only: bool = True
    def to_dict(self): return asdict(self)


def stable_outcome_id(tenant_id, program_id): return sha256(f"{tenant_id}|{program_id}|improvement-outcome".encode()).hexdigest()[:24]
