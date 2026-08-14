"""Structured SOC investigation memory records."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import json


@dataclass
class InvestigationMemoryRecord:
    memory_id: str
    case_id: str
    investigation_type: str
    scenario: str
    risk_level: str
    confidence: float
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    reasoning_summary: dict[str, Any] = field(default_factory=dict)
    mitre_techniques: list[str] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    synthetic_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, default=str)


InvestigationMemory = InvestigationMemoryRecord
