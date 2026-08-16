from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StrategicEvolutionTrends:
    tenant_id: str
    trends_id: str
    evolution_trend: str = "insufficient_history"
    adaptation_signals: tuple = ()
    portfolio_alignment: str = "insufficient_history"
    executive_review_context: tuple = ()
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
