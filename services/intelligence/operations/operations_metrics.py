"""Stable contracts for the operations intelligence response."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationMetrics:
    total_cases: int = 0
    active_cases: int = 0
    closed_cases: int = 0
    reopened_cases: int = 0
    overdue_cases: int = 0
    average_resolution_time: float = 0.0
    average_confidence: float = 0.0
    high_risk_cases: int = 0
    evidence_review_pending: int = 0
    evidence_review_completed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalystMetrics:
    assigned_cases: int = 0
    completed_reviews: int = 0
    average_review_time: float = 0.0
    escalations: int = 0
    false_positive_rate: float = 0.0
    by_actor: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderMetrics:
    provider_health: dict[str, str] = field(default_factory=dict)
    failure_rate: dict[str, float] = field(default_factory=dict)
    unavailable_count: dict[str, int] = field(default_factory=dict)
    average_latency: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
