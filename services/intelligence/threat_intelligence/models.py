from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class ThreatIndicator:
    indicator_id: str
    indicator_type: str
    value: str
    source: str = "synthetic"
    confidence: float = 0.0
    tags: list[str] = field(default_factory=list)
    first_seen: str | None = None
    last_seen: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class ThreatMatch:
    indicator: ThreatIndicator
    matched_cases: list[str] = field(default_factory=list)
    matched_events: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    relationship_type: str = "indicator_reuse"
    evidence_refs: list[str] = field(default_factory=list)
    def to_dict(self):
        d = asdict(self); d["indicator"] = self.indicator.to_dict(); return d

@dataclass
class ThreatIntelligenceReport:
    case_id: str
    matched_indicators: list[ThreatMatch] = field(default_factory=list)
    threat_score: int = 0
    campaign_similarity: float = 0.0
    intelligence_summary: str = ""
    recommendations: list[str] = field(default_factory=list)
    synthetic_only: bool = True
    def to_dict(self):
        d = asdict(self); d["matched_indicators"] = [m.to_dict() for m in self.matched_indicators]; return d
