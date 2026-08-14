"""Serializable investigation decision contract."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationDecision:
    decision_id: str
    case_id: str
    verdict: str
    severity: str
    confidence: float
    rationale: str
    recommended_actions: list[str] = field(default_factory=list)
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    mitre_summary: list[str] = field(default_factory=list)
    synthetic_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
