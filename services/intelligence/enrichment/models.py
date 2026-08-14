from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Indicator:
    value: str
    type: str
    source: str = "offline"
    confidence: float = 0.0

@dataclass
class EnrichmentResult:
    indicator: Indicator
    risk_score: float = 0.0
    confidence: float = 0.0
    tags: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def public(self) -> dict:
        return {"indicator": {"value": self.indicator.value, "type": self.indicator.type, "source": self.indicator.source, "confidence": self.indicator.confidence}, "risk_score": self.risk_score, "confidence": self.confidence, "tags": list(self.tags), "findings": list(self.findings)}
