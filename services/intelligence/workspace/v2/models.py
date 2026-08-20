"""JSON-safe contract for the analyst workspace V2 projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.core.serialization import serialize


@dataclass(frozen=True)
class AnalystWorkspaceV2:
    investigation: dict[str, Any]
    verdict_summary: dict[str, Any]
    confidence_visualization: dict[str, Any]
    risk_explanation: dict[str, Any]
    evidence_references: tuple[dict[str, Any], ...] = ()
    missing_evidence: tuple[dict[str, Any], ...] = ()
    attack_sequence_timeline: tuple[dict[str, Any], ...] = ()
    mitre_mappings: tuple[dict[str, Any], ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    analyst_feedback: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize({
            "investigation": self.investigation,
            "verdict_summary": self.verdict_summary,
            "confidence_visualization": self.confidence_visualization,
            "risk_explanation": self.risk_explanation,
            "evidence_references": list(self.evidence_references),
            "missing_evidence": list(self.missing_evidence),
            "attack_sequence_timeline": list(self.attack_sequence_timeline),
            "mitre_mappings": list(self.mitre_mappings),
            "provenance": self.provenance,
            "analyst_feedback": self.analyst_feedback,
        })
