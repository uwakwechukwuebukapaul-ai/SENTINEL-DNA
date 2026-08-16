from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class OutcomeLearning:
    tenant_id: str
    learning_id: str
    outcome_status: str = "insufficient_outcomes"
    observed_outcomes: tuple = ()
    learning_signals: tuple = ()
    historical_patterns: tuple = ()
    temporal_associations: tuple = ()
    evidence_quality: str = "insufficient_outcomes"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
