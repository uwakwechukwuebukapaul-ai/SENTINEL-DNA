"""Structured investigation report contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationReport:
    case_id: str
    title: str
    summary: str
    severity: str
    risk: Any = field(default_factory=dict)
    confidence: float = 0.0
    findings: list[Any] = field(default_factory=list)
    recommendations: list[Any] = field(default_factory=list)
    timeline: list[Any] = field(default_factory=list)
    mitre: list[str] = field(default_factory=list)
    attack_story: Any = None
    iocs: list[Any] = field(default_factory=list)
    evidence_summary: Any = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
