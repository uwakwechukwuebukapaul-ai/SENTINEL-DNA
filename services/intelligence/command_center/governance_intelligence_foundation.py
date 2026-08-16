from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class GovernanceIntelligenceFoundation:
    tenant_id: str; foundation_id: str; automation_readiness: str="insufficient_evidence"; governance_workflow_intelligence: str="insufficient_history"; policy_alignment_signals: tuple=(); human_oversight_requirements: tuple=("human_review_required",); evidence_strength: str="insufficient_evidence"; uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
