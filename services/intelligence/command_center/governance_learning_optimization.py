from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GovernanceLearningOptimization:
    tenant_id: str
    optimization_id: str
    posture: str = "insufficient_evidence"
    learning_signals: tuple = ()
    optimization_considerations: tuple = ()
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
