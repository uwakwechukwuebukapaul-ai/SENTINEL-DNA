from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class ExposureFactor:
    name: str
    value: float
    weight: float
    source: str = "unknown"
    def to_dict(self): return asdict(self)

@dataclass
class SecurityExposure:
    exposure_id: str
    tenant_id: str | None
    asset_id: str
    score: float
    severity: str
    factors: list[ExposureFactor] = field(default_factory=list)
    business_impact: str = "unknown"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return {**asdict(self), "factors": [x.to_dict() for x in self.factors]}

@dataclass
class RiskPriority:
    exposure_id: str
    rank: int
    priority: str
    rationale: str
    def to_dict(self): return asdict(self)

@dataclass
class RemediationRecommendation:
    exposure_id: str
    recommendation: str
    rationale: str
    requires_human_approval: bool = True
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
