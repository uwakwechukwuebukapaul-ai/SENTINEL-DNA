from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

def _value(value: Any) -> Any:
    return value.to_dict() if hasattr(value, "to_dict") else value

@dataclass
class WorkspaceTimelineEntry:
    timestamp: Any = None
    event_type: str = "unknown"
    source: str = "unknown"
    description: str = ""
    severity: str = "unknown"
    reference_id: str | None = None
    def to_dict(self): return asdict(self)

@dataclass
class SOCWorkspaceSnapshot:
    investigation_id: str | None = None
    case_id: str | None = None
    severity: str = "unknown"
    status: str = "unknown"
    analyst_assignment: Any = None
    investigation_summary: Any = None
    evidence_summary: Any = None
    threat_intelligence_summary: Any = None
    reasoning_summary: Any = None
    decision_summary: Any = None
    detection_summary: Any = None
    attack_path_summary: Any = None
    recommendation_summary: Any = None
    soar_summary: Any = None
    compliance_summary: Any = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    availability: str = "complete"
    def to_dict(self): return {key: _value(value) for key, value in asdict(self).items()}

@dataclass
class WorkspaceCaseView:
    case_information: Any = None
    timeline: list[Any] = field(default_factory=list)
    evidence_references: list[Any] = field(default_factory=list)
    ioc_references: list[Any] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    ai_confidence: float | None = None
    risk_posture: Any = None
    availability: str = "complete"
    def to_dict(self): return {key: _value(value) for key, value in asdict(self).items()}
