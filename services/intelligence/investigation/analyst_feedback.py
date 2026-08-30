"""Immutable analyst outcome events for AI investigation evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any
from uuid import uuid4


class AnalystDecision(str, Enum):
    CONFIRMED = "confirmed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"
    ANALYST_NOTE = "analyst_note"


MAX_REASON_LENGTH = 2000
MAX_REFERENCE_LENGTH = 200
MAX_TIME_SAVED_MINUTES = 7 * 24 * 60


def _rating(value: Any, name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"invalid_{name}")
    try:
        normalized = int(str(value).strip()) if isinstance(value, str) else int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{name}") from exc
    if (not isinstance(value, str) and normalized != value) or not 1 <= normalized <= 5:
        raise ValueError(f"invalid_{name}")
    return normalized


def _time_saved(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("invalid_estimated_time_saved")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_estimated_time_saved") from exc
    if not math.isfinite(normalized) or normalized < 0 or normalized > MAX_TIME_SAVED_MINUTES:
        raise ValueError("invalid_estimated_time_saved")
    return normalized


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
    helpful_rating: int | None = None
    confidence_rating: int | None = None
    estimated_time_saved: float | None = None
    analyst_comments: str = ""
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
        helpful_rating = _rating(self.helpful_rating, "helpful_rating")
        confidence_rating = _rating(self.confidence_rating, "confidence_rating")
        estimated_time_saved = _time_saved(self.estimated_time_saved)
        comments = str(self.analyst_comments or reason).strip()
        if len(comments) > MAX_REASON_LENGTH:
            raise ValueError("analyst_comments_too_long")
        object.__setattr__(self, "helpful_rating", helpful_rating)
        object.__setattr__(self, "confidence_rating", confidence_rating)
        object.__setattr__(self, "estimated_time_saved", estimated_time_saved)
        object.__setattr__(self, "analyst_comments", comments)
        for name in ("finding_id", "recommendation_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required(value, name))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
