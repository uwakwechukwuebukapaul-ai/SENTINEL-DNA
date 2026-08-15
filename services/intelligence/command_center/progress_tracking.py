"""Immutable temporal executive progress contracts and deterministic classifiers."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json

STATES = ("new", "insufficient_data", "not_yet_measurable", "improving", "sustained_improvement", "stable", "stalled", "degrading", "regression", "persistent_regression", "recovery", "mixed", "indeterminate")
STATE_PRECEDENCE = {s: i for i, s in enumerate(("persistent_regression", "recovery", "sustained_improvement", "regression", "degrading", "improving", "stalled", "stable", "mixed", "not_yet_measurable", "insufficient_data", "new", "indeterminate"))}

def _id(kind, tenant_id, *parts):
    payload = json.dumps([kind, tenant_id, *parts], sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode()).hexdigest()[:24]

def stable_observation_id(tenant_id, program_id, dimension, period, score, state): return _id("observation", tenant_id, program_id, dimension, period, score, state)
def stable_transition_id(tenant_id, program_id, dimension, period, previous, current): return _id("transition", tenant_id, program_id, dimension, period, previous, current)
def stable_tracking_id(tenant_id, program_id, dimension): return _id("tracking", tenant_id, program_id, dimension)

@dataclass(frozen=True)
class ExecutiveProgressObservation:
    tenant_id: str; program_id: str; dimension: str; observation_period: str | None; state: str; score: float | None = None; score_delta: float | None = None; progress_percentage: float | None = None; trajectory: str = "unavailable"; effectiveness: str = "indeterminate"; confidence: float | None = None; evidence_strength: str = "insufficient"; uncertainty: tuple = (); provenance: dict = field(default_factory=dict); contributing_references: tuple = (); stable_id: str = ""
    def __post_init__(self):
        if not self.stable_id: object.__setattr__(self, "stable_id", stable_observation_id(self.tenant_id, self.program_id, self.dimension, self.observation_period, self.score, self.state))
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ExecutiveProgressTransition:
    tenant_id: str; program_id: str; dimension: str; from_state: str; to_state: str; transition_type: str; transition_period: str | None; score_delta: float | None = None; confidence: float | None = None; evidence_strength: str = "insufficient"; uncertainty: tuple = (); provenance: dict = field(default_factory=dict); contributing_references: tuple = (); stable_id: str = ""
    def __post_init__(self):
        if not self.stable_id: object.__setattr__(self, "stable_id", stable_transition_id(self.tenant_id, self.program_id, self.dimension, self.transition_period, self.from_state, self.to_state))
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ExecutiveProgressTracking:
    tenant_id: str; program_id: str; dimension: str; current_state: str; previous_state: str | None; trajectory: str; score: float | None; baseline_score: float | None; current_score: float | None; score_delta: float | None; improvement_velocity: str; sustainability: str; regression_status: str; recovery_status: str; observation_count: int; transition_count: int; first_observed_period: str | None; last_observed_period: str | None; confidence: float | None; evidence_strength: str; uncertainty: tuple = (); provenance: dict = field(default_factory=dict); contributing_references: tuple = (); recommendations: tuple = (); advisory_only: bool = True; stable_id: str = ""
    def __post_init__(self):
        if not self.stable_id: object.__setattr__(self, "stable_id", stable_tracking_id(self.tenant_id, self.program_id, self.dimension))
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ExecutiveProgressHistory:
    tenant_id: str; periods: tuple; overall_scores: tuple; overall_trajectory: str; current_progress_score: float | None; previous_progress_score: float | None; score_delta: float | None; progress_velocity: str; sustainability_rate: float | None; regression_rate: float | None; recovery_rate: float | None; improving_programs: tuple; sustained_programs: tuple; stalled_programs: tuple; regressing_programs: tuple; recovering_programs: tuple; strongest_dimension: str | None; weakest_dimension: str | None; highest_priority_regression: str | None; confidence: float | None; evidence_strength: str; uncertainty: tuple = (); provenance: dict = field(default_factory=dict); recommendations: tuple = (); advisory_only: bool = True
    def to_dict(self): return asdict(self)
