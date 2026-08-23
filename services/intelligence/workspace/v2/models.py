"""JSON-safe contract for the analyst workspace V2 projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.core.serialization import serialize


@dataclass(frozen=True)
class AnalystWorkspaceV2:
    investigation: dict[str, Any]
    incident_header: dict[str, Any] = field(default_factory=dict)
    journey_stages: tuple[dict[str, Any], ...] = ()
    verdict_summary: dict[str, Any] = field(default_factory=dict)
    confidence_visualization: dict[str, Any] = field(default_factory=dict)
    risk_explanation: dict[str, Any] = field(default_factory=dict)
    evidence_references: tuple[dict[str, Any], ...] = ()
    evidence_explanations: tuple[dict[str, Any], ...] = ()
    intelligence_panel: dict[str, Any] = field(default_factory=dict)
    attack_story: dict[str, Any] = field(default_factory=dict)
    reasoning_chain: tuple[dict[str, Any], ...] = ()
    missing_evidence: tuple[dict[str, Any], ...] = ()
    attack_sequence_timeline: tuple[dict[str, Any], ...] = ()
    mitre_mappings: tuple[dict[str, Any], ...] = ()
    report_sections: dict[str, Any] = field(default_factory=dict)
    analyst_actions: tuple[dict[str, Any], ...] = ()
    disposition_lifecycle: tuple[dict[str, Any], ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    analyst_feedback: dict[str, Any] = field(default_factory=dict)
    explainability: dict[str, Any] = field(default_factory=dict)
    decision_support: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize({
            "investigation": self.investigation,
            "incident_header": self.incident_header,
            "journey_stages": list(self.journey_stages),
            "verdict_summary": self.verdict_summary,
            "confidence_visualization": self.confidence_visualization,
            "risk_explanation": self.risk_explanation,
            "evidence_references": list(self.evidence_references),
            "evidence_explanations": list(self.evidence_explanations),
            "intelligence_panel": self.intelligence_panel,
            "attack_story": self.attack_story,
            "reasoning_chain": list(self.reasoning_chain),
            "missing_evidence": list(self.missing_evidence),
            "attack_sequence_timeline": list(self.attack_sequence_timeline),
            "mitre_mappings": list(self.mitre_mappings),
            "report_sections": self.report_sections,
            "analyst_actions": list(self.analyst_actions),
            "disposition_lifecycle": list(self.disposition_lifecycle),
            "provenance": self.provenance,
            "analyst_feedback": self.analyst_feedback,
            "explainability": self.explainability,
            "decision_support": self.decision_support,
        })
