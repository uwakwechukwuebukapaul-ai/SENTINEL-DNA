from datetime import datetime, timezone
from uuid import uuid4
class SupportService:
    SLA = {"critical": 4, "high": 8, "medium": 24, "low": 72}
    def __init__(self): self.tickets = {}
    def create(self, organization_id, title, severity="medium", description=""):
        if severity not in self.SLA: raise ValueError("invalid_severity")
        item = {"id": str(uuid4()), "organization_id": organization_id, "title": title, "description": description, "severity": severity, "sla_hours": self.SLA[severity], "status": "open", "created_at": datetime.now(timezone.utc).isoformat()}; self.tickets[item["id"]] = item; return item
    def update(self, ticket_id, organization_id, status):
        item = self.tickets.get(ticket_id)
        if not item or item["organization_id"] != organization_id: raise LookupError("ticket_not_found")
        item["status"] = status; return item
    def list(self, organization_id): return [x for x in self.tickets.values() if x["organization_id"] == organization_id]
