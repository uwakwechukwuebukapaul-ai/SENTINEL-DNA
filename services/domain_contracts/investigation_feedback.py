"""Canonical contract for structured analyst feedback on an investigation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


def _required(value: str, name: str) -> str:
    value = str(value).strip()
    if not value:
        raise ValueError(f"{name}_required")
    return value


@dataclass(frozen=True)
class InvestigationFeedback:
    """Lossless domain representation of Command Center investigation feedback."""

    feedback_id: str
    tenant_id: str
    investigation_id: str
    outcome_reference: str = ""
    analyst_reference: str = ""
    outcome_agreement: str = "unable_to_assess"
    evidence_sufficiency: str = "unable_to_assess"
    recommendation_usefulness: str = "not_applicable"
    confidence: float | None = None
    reason_codes: tuple[str, ...] = ()
    supporting_references: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        for name in ("feedback_id", "tenant_id", "investigation_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.confidence is not None and not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence_out_of_range")
        object.__setattr__(self, "reason_codes", tuple(str(x) for x in self.reason_codes))
        object.__setattr__(self, "supporting_references", tuple(str(x) for x in self.supporting_references))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reason_codes"] = list(self.reason_codes)
        data["supporting_references"] = list(self.supporting_references)
        return data
