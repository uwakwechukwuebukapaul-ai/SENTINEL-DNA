from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class InvestigationPlanScore:
    plan_id: str
    tenant_id: str | None
    efficiency: float
    estimated_steps: int
    rationale: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass
class InvestigationStepRecommendation:
    step: str
    order: int
    rationale: str
    unnecessary: bool = False
    def to_dict(self): return asdict(self)

@dataclass
class OptimizationResult:
    tenant_id: str | None
    plan_score: InvestigationPlanScore
    recommendations: list[InvestigationStepRecommendation] = field(default_factory=list)
    historical_comparison: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    def to_dict(self): return {**asdict(self), "plan_score": self.plan_score.to_dict(), "recommendations": [x.to_dict() for x in self.recommendations]}
