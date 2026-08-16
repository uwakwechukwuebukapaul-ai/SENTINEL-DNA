from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class IntelligenceOperatingModel:
    tenant_id: str; model_id: str; operating_model_maturity: str="insufficient_history"; capability_gaps: tuple=(); intelligence_adoption_signals: tuple=(); continuous_improvement_indicators: tuple=(); evidence_strength: str="insufficient_evidence"; uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
