from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ResponseOutcomeTrendAnalytics:
    tenant_id: str
    trend_id: str
    trend: str = "insufficient_outcomes"
    outcome_signals: tuple = ()
    interpretation: str = "Insufficient outcomes for trend interpretation."
    evidence_strength: str = "insufficient_outcomes"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
