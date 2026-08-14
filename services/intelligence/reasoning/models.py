"""Serializable models produced by the evidence reasoning layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReasoningFinding:
    finding_id: str
    title: str
    description: str
    severity: str
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    reasoning_type: str = "deterministic_evidence_correlation"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningReport:
    summary: str
    findings: list[ReasoningFinding] = field(default_factory=list)
    confidence: float = 0.0
    generated_by: str = "EvidenceReasoner"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["findings"] = [finding.to_dict() for finding in self.findings]
        return data
