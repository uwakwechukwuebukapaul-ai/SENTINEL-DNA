"""Stable, JSON-safe contracts for reconstructed attack sequences."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.core.serialization import serialize


@dataclass
class AttackSequenceEvent:
    event_id: str
    timestamp: str
    stage: str
    description: str
    evidence_references: list[str] = field(default_factory=list)
    ioc_references: list[str] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    confidence: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(100.0, float(self.confidence)))
        self.evidence_references = [str(value) for value in self.evidence_references if value]
        self.ioc_references = [str(value) for value in self.ioc_references if value]
        self.mitre_techniques = [str(value) for value in self.mitre_techniques if value]
        self.provenance = serialize(self.provenance)

    def to_dict(self) -> dict[str, Any]:
        return serialize({
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "stage": self.stage,
            "description": self.description,
            "evidence_references": self.evidence_references,
            "ioc_references": self.ioc_references,
            "mitre_techniques": self.mitre_techniques,
            "confidence": self.confidence,
            "provenance": self.provenance,
        })


@dataclass
class AttackSequenceResult:
    investigation_id: str | None = None
    tenant_id: str | None = None
    events: list[AttackSequenceEvent] = field(default_factory=list)
    attack_story: str = "No evidence-backed attack sequence could be reconstructed."
    mitre_summary: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: list[str] = field(default_factory=list)
    missing_evidence: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(100.0, float(self.confidence)))
        self.events = [event if isinstance(event, AttackSequenceEvent) else AttackSequenceEvent(**event) for event in self.events]
        self.mitre_summary = serialize(self.mitre_summary)
        self.uncertainty = [str(value) for value in self.uncertainty if value]
        self.missing_evidence = serialize(self.missing_evidence)
        self.provenance = serialize(self.provenance)

    def to_dict(self) -> dict[str, Any]:
        return serialize({
            "investigation_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "events": [event.to_dict() for event in self.events],
            "attack_story": self.attack_story,
            "mitre_summary": self.mitre_summary,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "missing_evidence": self.missing_evidence,
            "provenance": self.provenance,
        })
