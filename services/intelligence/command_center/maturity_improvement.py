"""Immutable advisory maturity improvement contracts."""
from dataclasses import asdict, dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class ComparativeDimension:
    tenant_id: str; dimension_id: str; dimension_name: str; current_score_or_state: object; previous_score_or_state: object; delta: float | None; direction: str; relative_position: str; status: str; evidence_strength: str; confidence: float | None; uncertainty: list = field(default_factory=list); provenance: dict = field(default_factory=dict); contributing_references: list = field(default_factory=list)
    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class ImprovementPriority:
    priority_id: str; tenant_id: str; dimension_id: str; dimension_name: str; priority: str; severity: str; rationale: str; current_state: object; historical_state: object; trend: str; persistence: str; evidence_strength: str; confidence: float | None; uncertainty: list = field(default_factory=list); contributing_references: list = field(default_factory=list); advisory_only: bool = True
    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class ImprovementPlan:
    plan_id: str; tenant_id: str; dimension_id: str; dimension_name: str; objective: str; priority: str; rationale: str; evidence: list; recommended_focus: str; expected_outcome: str; measurement_criteria: list; confidence: float | None; uncertainty: list = field(default_factory=list); provenance: dict = field(default_factory=dict); contributing_references: list = field(default_factory=list); advisory_only: bool = True
    def to_dict(self): return asdict(self)


def stable_improvement_id(tenant_id, dimension_id, kind): return sha256(f"{tenant_id}|{dimension_id}|{kind}|maturity-improvement".encode()).hexdigest()[:24]
