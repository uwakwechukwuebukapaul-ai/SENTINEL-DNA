from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

@dataclass
class InvestigationQualityAssessment:
    investigation_id: str
    tenant_id: str | None
    overall_score: float
    evidence_score: float
    enrichment_score: float
    reasoning_score: float
    mitre_mapping_score: float
    timeline_score: float
    confidence_score: float
    completeness_score: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass
class QualityRecommendation:
    category: str
    severity: str
    explanation: str
    recommended_action: str
    requires_human_review: bool = True
    def to_dict(self): return asdict(self)

@dataclass
class QualityBenchmark:
    tenant_id: str | None
    average_score: float
    investigation_count: int
    improvement_trend: str
    def to_dict(self): return asdict(self)
