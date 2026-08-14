from datetime import datetime, timedelta, timezone
from .models import IncidentRecord, IncidentSLA

class IncidentSLAEngine:
    WINDOWS = {"critical": (15, 240), "high": (30, 480), "medium": (120, 1440), "low": (480, 2880)}
    def calculate(self, incident: IncidentRecord, now=None):
        now = now or datetime.now(timezone.utc); response, resolution = self.WINDOWS.get(incident.severity.lower(), self.WINDOWS["medium"]); created=datetime.fromisoformat(incident.created_at); response_deadline=created+timedelta(minutes=response); resolution_deadline=created+timedelta(minutes=resolution)
        return IncidentSLA(incident.incident_id, incident.severity, response_deadline.isoformat(), resolution_deadline.isoformat(), now > response_deadline and incident.status == "OPEN", now > resolution_deadline and incident.status != "CLOSED")
