from datetime import datetime, timezone
from uuid import uuid4
class PilotManagementService:
    def __init__(self): self.pilots = {}
    def create(self, organization_id, duration_days=30, success_criteria=None):
        item = {"id": str(uuid4()), "organization_id": organization_id, "duration_days": duration_days, "success_criteria": success_criteria or [], "users": [], "usage": {}, "feedback": [], "status": "active", "started_at": datetime.now(timezone.utc).isoformat()}; self.pilots[item["id"]] = item; return item
    def add_user(self, pilot_id, user_id): self.pilots[pilot_id]["users"].append(user_id); return self.pilots[pilot_id]
    def record_usage(self, pilot_id, metric, value=1): self.pilots[pilot_id]["usage"][metric] = self.pilots[pilot_id]["usage"].get(metric, 0) + value; return self.pilots[pilot_id]
    def feedback(self, pilot_id, value): self.pilots[pilot_id]["feedback"].append(value); return self.pilots[pilot_id]
    def list(self, organization_id): return [x for x in self.pilots.values() if x["organization_id"] == organization_id]
