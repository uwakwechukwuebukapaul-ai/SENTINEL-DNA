from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class StrategicIntelligenceHealth:
    tenant_id: str
    health_id: str
    coverage_score: int | float | None = None
    coverage_posture: str = "insufficient_history"
    confidence_distribution: tuple = ()
    evidence_quality_view: str = "insufficient_evidence"
    uncertainty_analysis: tuple = ()
    missing_intelligence_areas: tuple = ()
    maturity_gaps: tuple = ()
    evidence_strength: str = "insufficient_evidence"
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
