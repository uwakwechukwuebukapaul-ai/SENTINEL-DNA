from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class ThreatHypothesis:
    hypothesis_id: str
    tenant_id: str | None
    title: str
    rationale: str
    mitre_techniques: list[str] = field(default_factory=list)
    confidence: float = 0.0
    requires_human_approval: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass
class HuntingQuery:
    query_id: str
    tenant_id: str | None
    query_type: str
    query: str
    mitre_techniques: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass
class HuntingEvidence:
    evidence_id: str
    tenant_id: str | None
    source: str
    value: Any
    relevance: float = 0.0
    def to_dict(self): return asdict(self)

@dataclass
class HuntingResult:
    query_id: str
    tenant_id: str | None
    matches: list[HuntingEvidence] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
    def to_dict(self): return {**asdict(self), "matches": [x.to_dict() for x in self.matches]}
