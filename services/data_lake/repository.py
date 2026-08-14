from datetime import datetime
from .models import SecurityEventRecord
from .storage import InMemoryEventStorage

class SecurityEventRepository:
    def __init__(self, storage=None): self.storage = storage or InMemoryEventStorage()
    def store(self, event): return self.storage.append(event)
    def bulk_store(self, events): return self.storage.extend(events)
    def list(self, organization_id): return [e for e in self.storage.events if e.organization_id == organization_id]
    def query(self, organization_id, filters=None):
        filters = filters or {}; events = self.list(organization_id)
        def matches(e):
            for key in ("asset_id", "user_id", "severity", "event_type", "source"):
                if filters.get(key) and getattr(e, key, None) != filters[key]: return False
            if filters.get("ip") and filters["ip"] not in str(e.raw_event): return False
            if filters.get("ioc") and filters["ioc"] not in e.ioc_matches: return False
            techniques = filters.get("mitre") or filters.get("technique")
            if techniques and techniques not in e.mitre_mapping: return False
            for bound, before in (("start", True), ("end", False)):
                if filters.get(bound):
                    value, target = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")), datetime.fromisoformat(filters[bound].replace("Z", "+00:00"))
                    if (value < target if before else value > target): return False
            return True
        return [e for e in events if matches(e)]
