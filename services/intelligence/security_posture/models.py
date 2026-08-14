from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class SecurityDomainScore:
    domain: str
    score: float
    weight: float
    status: str = "developing"
    def to_dict(self): return asdict(self)

@dataclass
class PostureRecommendation:
    domain: str
    recommendation: str
    rationale: str
    priority: str = "medium"
    advisory_only: bool = True
    def to_dict(self): return asdict(self)

@dataclass
class SecurityPostureScore:
    tenant_id: str | None
    overall_score: float
    domain_scores: list[SecurityDomainScore] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return {**asdict(self), "domain_scores": [x.to_dict() for x in self.domain_scores]}
