from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ImprovementTrends:
    tenant_id: str
    trends_id: str
    improvement_trend: str = "insufficient_history"
    governance_learning_trend: str = "insufficient_history"
    response_outcome_trend: str = "insufficient_outcomes"
    portfolio_posture_trajectory: str = "insufficient_history"
    observed_patterns: tuple = ()
    interpretation: str = "Insufficient history for longitudinal interpretation."
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
