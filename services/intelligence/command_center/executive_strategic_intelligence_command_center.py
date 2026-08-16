from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class ExecutiveStrategicIntelligenceCommandCenter:
    tenant_id: str
    command_center_id: str
    strategic_intelligence_health: str = "insufficient_history"
    organizational_intelligence_posture: str = "insufficient_history"
    portfolio_summary: tuple = ()
    cross_domain_signals: tuple = ()
    maturity_overview: str = "insufficient_history"
    governance_posture: str = "insufficient_evidence"
    strategic_evolution_status: str = "insufficient_history"
    improvement_trajectory: str = "insufficient_history"
    executive_attention_areas: tuple = ()
    confidence: str | float | None = None
    evidence_strength: str = "insufficient_evidence"
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
