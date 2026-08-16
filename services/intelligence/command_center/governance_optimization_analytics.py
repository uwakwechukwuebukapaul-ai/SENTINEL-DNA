from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GovernanceOptimizationAnalytics:
    tenant_id: str
    analytics_id: str
    posture: str = "insufficient_evidence"
    opportunities: tuple = ()
    optimization_readiness: str = "insufficient_evidence"
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
