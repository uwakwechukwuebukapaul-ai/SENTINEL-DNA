from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ExecutiveIntelligenceOperatingSystem:
    tenant_id: str; operating_system_id: str; unified_operating_posture: str="insufficient_history"; cross_domain_intelligence_availability: str="insufficient_history"; intelligence_capability_registry: tuple=(); executive_operating_readiness: str="insufficient_evidence"; intelligence_workflow_visibility: str="insufficient_history"; evidence_strength: str="insufficient_evidence"; confidence: str|float|None=None; uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
