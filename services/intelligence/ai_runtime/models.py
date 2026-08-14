from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class AIResponse:
    content: str
    confidence: float = 0.0
    evidence_references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        return {"content": self.content, "confidence": self.confidence, "evidence_references": list(self.evidence_references), "metadata": dict(self.metadata)}
