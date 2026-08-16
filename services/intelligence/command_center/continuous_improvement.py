from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ContinuousImprovement:
    tenant_id: str
    improvement_id: str
    opportunities: tuple = ()
    learning_priorities: tuple = ()
    effectiveness_indicators: tuple = ()
    readiness: str = "insufficient_evidence"
    next_step_considerations: tuple = ()
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
