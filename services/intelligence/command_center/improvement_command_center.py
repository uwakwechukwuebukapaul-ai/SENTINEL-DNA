from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ImprovementCommandCenter:
    tenant_id: str
    command_center_id: str
    posture: str = "insufficient_history"
    initiative_signals: tuple = ()
    portfolio_improvement_posture: str = "insufficient_history"
    trend_interpretation: str = "Insufficient history for trend interpretation."
    executive_context: tuple = ()
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
