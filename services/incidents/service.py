from datetime import datetime, timezone
from uuid import uuid4
class IncidentService:
    STATES = {"new", "triaged", "investigating", "contained", "resolved", "closed"}
    def __init__(self): self.items = {}
    def create(self, organization_id, title, severity="medium", owner_id=None, sla_minutes=60):
        item = {"id": str(uuid4()), "organization_id": organization_id, "title": title, "severity": severity, "state": "new", "owner_id": owner_id, "escalated": False, "sla_minutes": sla_minutes, "created_at": datetime.now(timezone.utc).isoformat(), "resolution": None, "post_incident_review": None}; self.items[item["id"]] = item; return item
    def transition(self, incident_id, organization_id, state, resolution=None):
        item = self.items.get(incident_id)
        if not item or item["organization_id"] != organization_id: raise LookupError("incident_not_found")
        if state not in self.STATES: raise ValueError("invalid_incident_state")
        item["state"] = state; item["resolution"] = resolution or item["resolution"]; return item
    def list(self, organization_id): return [x for x in self.items.values() if x["organization_id"] == organization_id]
    def review(self, incident_id, organization_id, review):
        item = self.items.get(incident_id)
        if not item or item["organization_id"] != organization_id: raise LookupError("incident_not_found")
        item["post_incident_review"] = review; return item
