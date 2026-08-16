from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ExecutiveIntelligenceOperatingModel:
    tenant_id: str
    operating_model_id: str
    intelligence_operating_posture: str = "insufficient_history"
    intelligence_lifecycle_visibility: str = "insufficient_history"
    executive_intelligence_ownership_model: str = "advisory_review_required"
    intelligence_review_cadence: str = "insufficient_history"
    governance_readiness: str = "insufficient_evidence"
    intelligence_adoption_posture: str = "insufficient_history"
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
