from datetime import datetime, timezone
from uuid import uuid4
class CollaborationService:
    def __init__(self): self.comments = {}; self.actions = {}
    def comment(self, incident_id, organization_id, user_id, message, kind="comment"):
        item = {"id": str(uuid4()), "incident_id": incident_id, "organization_id": organization_id, "user_id": user_id, "message": message, "kind": kind, "created_at": datetime.now(timezone.utc).isoformat()}; self.comments.setdefault(incident_id, []).append(item); return item
    def list_comments(self, incident_id, organization_id): return [x for x in self.comments.get(incident_id, []) if x["organization_id"] == organization_id]
    def action(self, incident_id, organization_id, user_id, action, metadata=None):
        item = {"incident_id": incident_id, "organization_id": organization_id, "user_id": user_id, "action": action, "metadata": metadata or {}, "timestamp": datetime.now(timezone.utc).isoformat()}; self.actions.setdefault(incident_id, []).append(item); return item
    def list_actions(self, incident_id, organization_id): return [x for x in self.actions.get(incident_id, []) if x["organization_id"] == organization_id]
