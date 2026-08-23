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
    evidence_status: str = "not_attached"
    intelligence_provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningReport:
    summary: str
    findings: list[ReasoningFinding] = field(default_factory=list)
    confidence: float = 0.0
    generated_by: str = "EvidenceReasoner"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def evidence_refs(self) -> list[str]:
        """All evidence supporting this report, in stable order."""
        refs: list[str] = []
        for finding in self.findings:
            for reference in finding.evidence_refs:
                if reference not in refs:
                    refs.append(reference)
        return refs

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["findings"] = [finding.to_dict() for finding in self.findings]
        data["evidence_refs"] = self.evidence_refs
        return data
