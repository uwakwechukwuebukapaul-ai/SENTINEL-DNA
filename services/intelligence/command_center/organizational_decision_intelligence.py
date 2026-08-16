from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class OrganizationalDecisionIntelligence:
    tenant_id: str
    profile_id: str
    posture: str = "insufficient_history"
    decision_readiness_signals: tuple = ()
    strategic_alignment_indicators: tuple = ()
    improvement_capacity_indicators: tuple = ()
    governance_maturity_indicators: tuple = ()
    intelligence_coverage_analysis: str = "insufficient_history"
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
