from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class StrategicDecisionLifecycle:
    tenant_id: str; lifecycle_id: str; decision_preparation_posture: str="insufficient_history"; evidence_readiness: str="insufficient_evidence"; intelligence_availability: str="insufficient_history"; review_readiness: str="insufficient_history"; decision_lifecycle_maturity: str="insufficient_history"; feedback_opportunity_areas: tuple=(); uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
