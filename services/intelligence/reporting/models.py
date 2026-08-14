"""Serializable narrative reporting contract."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class InvestigationNarrative:
    report_id: str
    case_id: str
    title: str
    executive_summary: str
    analyst_summary: str
    incident_story: str
    evidence_timeline: list[dict[str, Any]] = field(default_factory=list)
    attack_analysis: str = ""
    mitre_analysis: list[str] = field(default_factory=list)
    decision_summary: str = ""
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    synthetic_only: bool = True

    def to_dict(self) -> dict[str, Any]: return asdict(self)
