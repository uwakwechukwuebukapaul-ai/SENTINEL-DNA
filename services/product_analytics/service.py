from datetime import datetime, timezone
class ProductAnalyticsService:
    def __init__(self): self.events = []
    def track(self, organization_id, category, name, user_id=None, properties=None):
        item = {"organization_id": organization_id, "category": category, "name": name, "user_id": user_id, "properties": properties or {}, "timestamp": datetime.now(timezone.utc).isoformat()}; self.events.append(item); return item
    def summary(self, organization_id):
        records = [x for x in self.events if x["organization_id"] == organization_id]; return {"organization_id": organization_id, "users": len({x["user_id"] for x in records if x["user_id"]}), "events": len(records), "investigations": sum(x["category"] == "investigation" for x in records), "ai_usage": sum(x["category"] == "ai" for x in records), "automation_usage": sum(x["category"] == "automation" for x in records), "reports": sum(x["category"] == "report" for x in records)}
