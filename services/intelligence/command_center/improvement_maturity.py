from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ImprovementMaturity:
    tenant_id: str
    maturity_id: str
    posture: str = "insufficient_history"
    maturity_signals: tuple = ()
    capability_evolution: tuple = ()
    improvement_readiness: str = "insufficient_evidence"
    trend: str = "insufficient_history"
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
