from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StrategicEvolution:
    tenant_id: str
    evolution_id: str
    posture: str = "insufficient_history"
    improvement_trend: str = "insufficient_history"
    governance_learning_trend: str = "insufficient_history"
    response_outcome_trend: str = "insufficient_outcomes"
    convergence: str = "insufficient_history"
    capability_signals: tuple = ()
    observed_patterns: tuple = ()
    modeled_interpretation: str = "Insufficient history for strategic evolution interpretation."
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
