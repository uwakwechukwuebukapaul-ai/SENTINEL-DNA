from datetime import datetime, timezone
from .models import IncidentRecord, IncidentTimeline

STATUSES = ("OPEN", "TRIAGED", "INVESTIGATING", "CONTAINMENT", "REMEDIATION", "RECOVERY", "CLOSED")
ALLOWED = {current: set(STATUSES[index:]) for index, current in enumerate(STATUSES)}

class IncidentLifecycleEngine:
    def transition(self, incident: IncidentRecord, status: str, actor=None, note=""):
        status = status.upper()
        if status not in STATUSES or status not in ALLOWED.get(incident.status, set()): raise ValueError("invalid incident lifecycle transition")
        incident.status=status; incident.updated_at=datetime.now(timezone.utc).isoformat(); return IncidentTimeline(incident.incident_id, status, actor, note)
