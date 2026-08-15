from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GovernanceLearningCorrelation:
    tenant_id: str
    correlation_id: str
    interpretation: str = "insufficient_history"
    learning_themes: tuple = ()
    response_relationships: tuple = ()
    association_boundary: str = "Observed temporal association only; no causal relationship is established."
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
