"""Immutable analyst outcome events for AI investigation evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AnalystDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


MAX_REASON_LENGTH = 2000
MAX_REFERENCE_LENGTH = 200


def _required(value: Any, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{name}_required")
    if len(normalized) > MAX_REFERENCE_LENGTH:
        raise ValueError(f"{name}_too_long")
    return normalized


@dataclass(frozen=True)
class AnalystFeedback:
    """A server-authored, append-only analyst decision about an investigation."""

    feedback_id: str = field(default_factory=lambda: f"FB-{uuid4().hex}")
    investigation_id: str = ""
    case_id: str = ""
    decision: str = ""
    analyst_id: str = ""
    finding_id: str | None = None
    recommendation_id: str | None = None
    reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tenant_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("feedback_id", "investigation_id", "case_id", "analyst_id", "tenant_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        decision = str(self.decision or "").strip().lower()
        if decision not in {item.value for item in AnalystDecision}:
            raise ValueError("invalid_decision")
        object.__setattr__(self, "decision", decision)
        reason = str(self.reason or "").strip()
        if len(reason) > MAX_REASON_LENGTH:
            raise ValueError("reason_too_long")
        object.__setattr__(self, "reason", reason)
        for name in ("finding_id", "recommendation_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required(value, name))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
