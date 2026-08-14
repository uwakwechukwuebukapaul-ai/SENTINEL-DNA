from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class IncidentWorkflow:
    incident_id: str; organization_id: str; state: str = "NEW"; history: list[dict] = field(default_factory=list); timestamps: dict = field(default_factory=dict)
    def public(self): return asdict(self)
