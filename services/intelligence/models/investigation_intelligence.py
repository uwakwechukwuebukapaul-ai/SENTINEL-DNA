"""Unified, JSON-ready investigation intelligence contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationIntelligence:
    findings: list[Any] = field(default_factory=list)
    recommendations: list[Any] = field(default_factory=list)
    risk_score: float = 0.0
    risk_severity: str = "unknown"
    confidence: float = 0.0
    mitre_techniques: list[str] = field(default_factory=list)
    attack_story: Any = None
    iocs: list[Any] = field(default_factory=list)
    evidence_summary: Any = field(default_factory=dict)
    timeline: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.findings, list):
            self.findings = list(self.findings or [])
        if not isinstance(self.recommendations, list):
            self.recommendations = list(self.recommendations or [])
        if not isinstance(self.iocs, list):
            self.iocs = list(self.iocs or [])
        if not isinstance(self.timeline, list):
            self.timeline = list(self.timeline or [])
        if not isinstance(self.metadata, dict):
            self.metadata = dict(self.metadata or {})
        self.risk_score = float(self.risk_score or 0)
        self.confidence = max(0.0, min(1.0, float(self.confidence or 0)))
        self.risk_severity = str(self.risk_severity or "unknown").lower()
        self.mitre_techniques = [
            str(technique)
            for technique in (self.mitre_techniques or [])
            if technique
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
