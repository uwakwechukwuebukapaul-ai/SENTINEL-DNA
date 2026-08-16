from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class DecisionIntelligenceFoundation:
    tenant_id: str; foundation_id: str; decision_intelligence_readiness: str="insufficient_history"; evidence_to_decision_traceability: str="insufficient_evidence"; decision_context_completeness: str="insufficient_history"; decision_lifecycle_visibility: str="insufficient_history"; strategic_decision_support_signals: tuple=(); uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
