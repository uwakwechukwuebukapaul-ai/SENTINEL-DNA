from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ExecutiveGovernanceSummary:
    tenant_id: str
    summary_id: str
    executive_governance_posture: str = "insufficient_history"
    maturity_summary: str = "insufficient_history"
    strategic_review_areas: tuple = ()
    improvement_opportunities: tuple = ()
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
