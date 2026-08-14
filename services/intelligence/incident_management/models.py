from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class IncidentRecord:
    incident_id: str
    tenant_id: str | None
    title: str
    severity: str = "medium"
    status: str = "OPEN"
    business_impact: str = "unknown"
    case_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None
    def to_dict(self): return asdict(self)

@dataclass
class IncidentTimeline:
    incident_id: str
    status: str
    actor: str | None = None
    note: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass
class IncidentSLA:
    incident_id: str
    severity: str
    response_deadline: str
    resolution_deadline: str
    response_breached: bool = False
    resolution_breached: bool = False
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class EscalationRule:
    rule_id: str
    minimum_severity: str = "high"
    breach_required: bool = False
    business_impacts: tuple[str, ...] = ("high", "critical")
    def to_dict(self): return asdict(self)

@dataclass
class ClosureReport:
    incident_id: str
    tenant_id: str | None
    closed_at: str
    root_cause: str = "unknown"
    lessons_learned: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)
