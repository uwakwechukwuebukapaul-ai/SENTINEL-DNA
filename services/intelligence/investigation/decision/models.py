"""Provider-neutral, evidence-backed decision intelligence contracts."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from services.core.serialization import serialize

@dataclass
class DecisionResult:
    verdict: str = "inconclusive"
    confidence: float = 0.0
    risk_score: float = 0.0
    rationale: str = "Insufficient evidence for a supported decision."
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    missing_evidence: list[dict[str, Any]] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    containment_guidance: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    investigation_id: str | None = None
    tenant_id: str | None = None
    # Legacy compatibility fields.
    case_id: str | None = None
    decision: str | None = None
    priority: str | None = None
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(100.0, float(self.confidence)))
        self.risk_score = max(0.0, min(100.0, float(self.risk_score)))
        self.case_id = self.case_id or self.investigation_id
        self.investigation_id = self.investigation_id or self.case_id
        self.actions = list(self.actions or self.recommended_actions)
        self.recommended_actions = list(self.recommended_actions or self.actions)
        self.decision = self.decision or self.verdict
        self.priority = self.priority or ("P1" if self.risk_score >= 75 else "P2" if self.risk_score >= 45 else "P3")
        # This is a durable boundary contract, not an object graph.  In
        # particular, never retain an InvestigationResult, InvestigationReport,
        # coordinator, or runtime object supplied by a caller.
        self.supporting_evidence = serialize(self.supporting_evidence)
        self.missing_evidence = serialize(self.missing_evidence)
        self.recommended_actions = serialize(self.recommended_actions)
        self.containment_guidance = serialize(self.containment_guidance)
        self.provenance = serialize(self.provenance)
        self.actions = serialize(self.actions)
        self.metadata = serialize(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return serialize({
            "verdict": self.verdict,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "rationale": self.rationale,
            "supporting_evidence": self.supporting_evidence,
            "missing_evidence": self.missing_evidence,
            "recommended_actions": self.recommended_actions,
            "containment_guidance": self.containment_guidance,
            "provenance": self.provenance,
            "investigation_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "decision": self.decision,
            "priority": self.priority,
            "actions": self.actions,
            "metadata": self.metadata,
        })
