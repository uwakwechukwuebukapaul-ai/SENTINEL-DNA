from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
def now(): return datetime.now(timezone.utc).isoformat()
def _dict(value): return value.to_dict() if hasattr(value, "to_dict") else value
@dataclass
class InvestigationOverview:
    investigation_id: str; case_id: str | None = None; status: str = "unknown"; severity: str = "unknown"; summary: Any = None; evidence_count: int = 0; ai_confidence: float | None = None; risk_posture: Any = None
    def to_dict(self): return {key: _dict(value) for key, value in asdict(self).items()}
@dataclass
class ThreatPostureView:
    threat_score: float = 0.0; mitre_techniques: list[str] = field(default_factory=list); vulnerability_count: int = 0; attack_path_count: int = 0; availability: str = "complete"
    def to_dict(self): return asdict(self)
@dataclass
class DecisionQueueItem:
    decision_id: str; decision_type: str; title: str; description: str = ""; tenant_id: str | None = None; investigation_id: str | None = None; priority: str = "medium"; requires_human_approval: bool = True; status: str = "pending"; created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)
@dataclass
class ExecutivePostureSummary:
    active_investigations: int = 0; critical_investigations: int = 0; pending_decisions: int = 0; threat_score: float = 0.0; detection_posture: Any = None; agent_activity: Any = None; availability: str = "complete"
    def to_dict(self): return {key: _dict(value) for key, value in asdict(self).items()}
@dataclass
class SOCCommandSnapshot:
    tenant_id: str | None = None; generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat()); investigations: list[InvestigationOverview] = field(default_factory=list); threat_posture: ThreatPostureView = field(default_factory=ThreatPostureView); executive_posture: ExecutivePostureSummary = field(default_factory=ExecutivePostureSummary); pending_decisions: list[DecisionQueueItem] = field(default_factory=list); availability: str = "complete"
    def to_dict(self): return {key: [_dict(item) for item in value] if isinstance(value, list) else _dict(value) for key, value in asdict(self).items()}

@dataclass
class CommandCenterContext:
    tenant_id: str
    generated_at: str = field(default_factory=now)
    overview: dict = field(default_factory=dict)
    attention: list = field(default_factory=list)
    investigations: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    risk: list = field(default_factory=list)
    compliance: list = field(default_factory=list)
    governance: list = field(default_factory=list)
    operations: list = field(default_factory=list)
    lifecycle: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    executive: dict = field(default_factory=dict)
    copilot_context: dict = field(default_factory=dict)
    subsystem_availability: dict = field(default_factory=dict)
    uncertainty: str = "UNKNOWN"
    advisory: bool = True
    requires_human_review: bool = True
    def to_dict(self): return self.__dict__.copy()
