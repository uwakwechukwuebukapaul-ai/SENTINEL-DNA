from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ImprovementGovernance:
    tenant_id: str
    governance_id: str
    portfolio_posture: str = "insufficient_history"
    priorities: tuple = ()
    governance_status: str = "insufficient_evidence"
    blockers: tuple = ()
    evidence_strength: str = "insufficient_evidence"
    confidence: str | float | None = None
    uncertainty: tuple = ()
    provenance: tuple = ()
    advisory_only: bool = True

    def to_dict(self):
        return asdict(self)
