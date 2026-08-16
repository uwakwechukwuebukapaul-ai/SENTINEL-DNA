from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ImprovementMaturityAnalytics:
    tenant_id: str
    analytics_id: str
    posture: str = "insufficient_history"
    progression_interpretation: str = "Insufficient history for maturity progression interpretation; no causal relationship is established."
    capability_signals: tuple = ()
    lifecycle_visibility: tuple = ()
    longitudinal_trend: str = "insufficient_history"
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
