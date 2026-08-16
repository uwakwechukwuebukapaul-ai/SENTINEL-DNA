from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ExecutiveIntelligenceSummary:
    tenant_id: str
    summary_id: str
    executive_summary: str = "Insufficient history for an executive intelligence summary."
    strategic_posture: str = "insufficient_history"
    emerging_opportunities: tuple = ()
    emerging_risks: tuple = ()
    recommended_review_areas: tuple = ()
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
