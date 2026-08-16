"""Implementation-independent contracts for the investigation feedback loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class OutcomeStatus(_StringEnum):
    UNKNOWN = "UNKNOWN"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class FeedbackOutcome(_StringEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class QualityScope(_StringEnum):
    INVESTIGATION = "investigation"
    OUTCOME = "outcome"


def _required(value: str, name: str) -> str:
    value = str(value).strip()
    if not value:
        raise ValueError(f"{name}_required")
    return value


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


@dataclass(frozen=True)
class Outcome:
    """Normalized result of a lifecycle-owned investigation action."""

    tenant_id: str
    lifecycle_id: str
    outcome_id: str
    status: OutcomeStatus = OutcomeStatus.UNKNOWN
    case_id: str = ""
    investigation_id: str = ""
    verification_status: OutcomeStatus = OutcomeStatus.UNKNOWN
    decision_reference: str = ""
    action_reference: str = ""
    evidence_references: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", _required(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "lifecycle_id", _required(self.lifecycle_id, "lifecycle_id"))
        object.__setattr__(self, "outcome_id", _required(self.outcome_id, "outcome_id"))
        object.__setattr__(self, "evidence_references", tuple(str(x) for x in self.evidence_references))
        object.__setattr__(self, "provenance", _mapping(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["verification_status"] = self.verification_status.value
        data["evidence_references"] = list(self.evidence_references)
        return data


@dataclass(frozen=True)
class Feedback:
    """Analyst feedback attached to a decision or outcome."""

    feedback_id: str
    tenant_id: str
    user_id: str
    decision_id: str
    outcome: FeedbackOutcome
    correction: str | None = None
    confidence: float | None = None
    outcome_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("feedback_id", "tenant_id", "user_id", "decision_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.confidence is not None and not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence_out_of_range")
        object.__setattr__(self, "provenance", _mapping(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        return data


@dataclass(frozen=True)
class QualityAssessment:
    """A scoped quality result; investigation and outcome quality remain distinct."""

    assessment_id: str
    tenant_id: str
    subject_id: str
    scope: QualityScope
    score: float
    human_review_required: bool = True
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("assessment_id", "tenant_id", "subject_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if not 0 <= float(self.score) <= 100:
            raise ValueError("score_out_of_range")
        object.__setattr__(self, "provenance", _mapping(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.value
        return data


@dataclass(frozen=True)
class LearningSignal:
    """Advisory, provenance-bearing input to learning and optimization consumers."""

    signal_id: str
    tenant_id: str
    signal_type: str
    source_id: str
    value: Mapping[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    advisory_only: bool = True
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("signal_id", "tenant_id", "signal_type", "source_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.confidence is not None and not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence_out_of_range")
        object.__setattr__(self, "value", _mapping(self.value))
        object.__setattr__(self, "provenance", _mapping(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
