from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class ExecutiveIntelligenceCommandCenter:
    tenant_id:str; command_center_id:str; unified_executive_intelligence_posture:str="insufficient_history"; intelligence_capability_health:str="insufficient_evidence"; operating_model_status:str="insufficient_history"; governance_intelligence_status:str="insufficient_evidence"; decision_intelligence_status:str="insufficient_history"; cross_domain_readiness_interpretation:str="Insufficient evidence for cross-domain readiness; advisory consideration only."; evidence_references:tuple=(); confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self):return asdict(self)
