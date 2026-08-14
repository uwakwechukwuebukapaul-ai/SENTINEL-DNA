from dataclasses import asdict, dataclass
from datetime import datetime, timezone

@dataclass
class RetentionPolicy:
    organization_id: str; retention_period: str = "90 days"; created_at: str = ""; updated_at: str = ""
    def public(self): return asdict(self)

class RetentionService:
    def __init__(self): self.policies = {}
    def get(self, organization_id):
        if organization_id not in self.policies:
            stamp = datetime.now(timezone.utc).isoformat(); self.policies[organization_id] = RetentionPolicy(organization_id, "90 days", stamp, stamp)
        return self.policies[organization_id]
    def set(self, organization_id, period):
        item = self.get(organization_id); item.retention_period = period; item.updated_at = datetime.now(timezone.utc).isoformat(); return item
