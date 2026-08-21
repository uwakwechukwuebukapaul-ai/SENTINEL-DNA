from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

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
    quality_id: str = field(default_factory=lambda: f"QUAL-{uuid4().hex}")
    case_id: str | None = None
    quality_status: str = "insufficient_data"
    evidence_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
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
