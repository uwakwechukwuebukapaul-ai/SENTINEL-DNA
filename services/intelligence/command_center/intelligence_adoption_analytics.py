from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class IntelligenceAdoptionAnalytics:
    tenant_id: str
    adoption_id: str
    usage_posture: str = "insufficient_history"
    adoption_readiness: str = "insufficient_evidence"
    coverage_gaps: tuple = ()
    maturity_blockers: tuple = ()
    enablement_opportunities: tuple = ()
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
