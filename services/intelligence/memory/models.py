"""Structured, tenant-scoped SOC investigation memory records."""
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
    # Additive fields are defaulted to preserve the historical constructor.
    tenant_id: str = "default"
    investigation_id: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    verdict: str = ""
    attack_pattern: list[str] = field(default_factory=list)
    evidence_fingerprint: str = ""
    validation_result: str = "validated"
    audit_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, default=str)


InvestigationMemory = InvestigationMemoryRecord


@dataclass(frozen=True)
class AnalystFeedbackRecord:
    """Append-only analyst feedback retained with memory provenance."""

    feedback_id: str
    tenant_id: str
    investigation_id: str
    analyst_id: str
    verdict: str
    confidence: float | None = None
    reason: str = ""
    evidence_references: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    audit_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
