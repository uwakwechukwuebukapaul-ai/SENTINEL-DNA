from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class IntelligenceFeedbackLoop:
    tenant_id: str; feedback_id: str; intelligence_usefulness_signals: tuple=(); improvement_opportunities: tuple=(); governance_learning_inputs: tuple=(); maturity_refinement_areas: tuple=(); uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
