"""Provider-neutral, evidence-backed decision intelligence contracts."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
