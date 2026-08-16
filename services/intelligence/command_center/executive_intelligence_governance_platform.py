from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ExecutiveIntelligenceGovernancePlatform:
    tenant_id: str; platform_id: str; governance_platform_posture: str="insufficient_history"; intelligence_lifecycle_governance: str="insufficient_history"; intelligence_ownership_visibility: str="insufficient_history"; governance_control_maturity: str="insufficient_evidence"; review_process_readiness: str="insufficient_history"; governance_evolution_signals: tuple=(); evidence_strength: str="insufficient_evidence"; uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
