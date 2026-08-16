from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class StrategicPortfolioGovernance:
    tenant_id: str
    governance_id: str
    portfolio_oversight_posture: str = "insufficient_history"
    governance_alignment_signals: tuple = ()
    strategic_priority_visibility: str = "insufficient_history"
    portfolio_maturity_indicators: tuple = ()
    review_attention_areas: tuple = ()
    evidence_strength: str = "insufficient_evidence"
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
