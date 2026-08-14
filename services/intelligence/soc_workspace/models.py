from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class SOCWorkspaceSnapshot:
    generated_at: str
    active_cases: int = 0
    high_risk_cases: int = 0
    critical_cases: int = 0
    threat_campaigns: int = 0
    active_hunts: int = 0
    average_ai_confidence: float = 0.0
    investigation_metrics: dict[str, Any] = field(default_factory=dict)
    synthetic_only: bool = True
    def to_dict(self): return asdict(self)

@dataclass
class CaseWorkspaceView:
    case_id: str
    severity: str = "unknown"
    status: str = "unknown"
    evidence_summary: Any = None
    threat_intelligence_summary: Any = None
    hunting_summary: Any = None
    reasoning_summary: Any = None
    decision_summary: Any = None
    copilot_summary: Any = None
    narrative_summary: Any = None
    def to_dict(self): return asdict(self)

@dataclass
class ThreatPostureSummary:
    total_cases: int = 0
    threat_score_average: float = 0.0
    top_indicators: list[str] = field(default_factory=list)
    top_campaigns: list[str] = field(default_factory=list)
    top_mitre_techniques: list[str] = field(default_factory=list)
    risk_distribution: dict[str, int] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class DetectionPostureSummary:
    total_rules: int = 0
    sigma_rules: int = 0
    mitre_coverage: Any = None
    detection_gaps: list[Any] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass
class SOARPostureSummary:
    total_playbooks: int = 0
    pending_approvals: int = 0
    completed_executions: int = 0
    blocked_actions: int = 0
    def to_dict(self): return asdict(self)

@dataclass
class IntegrationPostureSummary:
    total_connectors: int=0; active_connectors: int=0; unhealthy_connectors: int=0; last_sync: str|None=None
    def to_dict(self): return asdict(self)

@dataclass
class TenantPostureSummary:
    tenant_id: str; users: int=0; active_cases: int=0; investigations: int=0; detections: int=0; integrations: int=0
    def to_dict(self): return asdict(self)

@dataclass
class GovernancePostureSummary:
    active_policies: int=0; denied_actions: int=0; approval_requests: int=0; compliance_status: str="unknown"
    def to_dict(self): return asdict(self)

@dataclass
class SecurityPostureSummary:
    compliance_score: float=0.0; risk_score: float=0.0; control_coverage: float=0.0; open_findings: int=0; framework_status: dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class AttackSurfaceSummary:
    total_assets:int=0; critical_assets:int=0; exposed_assets:int=0; high_risk_assets:int=0; unknown_assets:int=0
    def to_dict(self): return asdict(self)

@dataclass
class VulnerabilityPostureSummary:
    total_vulnerabilities:int=0; critical_findings:int=0; high_risk_assets:int=0; exposed_vulnerabilities:int=0; remediation_priority:list[Any]=field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass
class SecurityGraphPostureSummary:
    total_entities:int=0; total_relationships:int=0; active_campaign_links:int=0; attack_paths_found:int=0; enriched_investigations:int=0
    def to_dict(self): return asdict(self)

@dataclass
class AttackPathPostureSummary:
    total_paths:int=0; critical_paths:int=0; high_exposure_assets:int=0; average_exposure_score:float=0.0; largest_blast_radius:int=0
    def to_dict(self): return asdict(self)

@dataclass
class ReasoningPostureSummary:
    active_hypotheses:int=0; average_confidence:float=0.0; prioritized_evidence_count:int=0; reasoning_quality_score:float=0.0
    def to_dict(self): return asdict(self)
