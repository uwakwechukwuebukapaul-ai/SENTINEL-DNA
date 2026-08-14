"""
Compatibility models.

Canonical models live in correlation_result.py
"""

from .correlation_result import CorrelationResult
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass(frozen=True)
class SecuritySignal:
    signal_id: str
    tenant_id: str | None
    signal_type: str
    value: Any = None
    source: str = "unknown"
    attributes: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class CorrelationRule:
    rule_id: str
    name: str
    signal_types: tuple[str, ...]
    threshold: float = .7
    description: str = ""
    def to_dict(self): return asdict(self)

@dataclass
class CorrelationAnalysisResult:
    tenant_id: str | None = None
    matched_rules: list[str] = field(default_factory=list)
    signals: list[SecuritySignal] = field(default_factory=list)
    confidence: float = 0.0
    risk: str = "unknown"
    false_positive: bool = False
    availability: str = "complete"
    def to_dict(self): return {**asdict(self), "signals": [x.to_dict() for x in self.signals]}

@dataclass(frozen=True)
class InvestigationTrigger:
    trigger_id: str
    tenant_id: str | None
    reason: str
    confidence: float
    risk: str
    signal_ids: tuple[str, ...] = ()
    requires_human_approval: bool = True
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

__all__ = [
    "CorrelationResult", "CorrelationAnalysisResult", "SecuritySignal", "CorrelationRule", "InvestigationTrigger",
]
