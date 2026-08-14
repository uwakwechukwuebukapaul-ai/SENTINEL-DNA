from datetime import datetime, timezone
from .models import ThreatFeed
from .repository import ThreatFeedRepository
class ThreatFeedService:
    def __init__(self): self.repository = ThreatFeedRepository()
    def create(self, organization_id, data):
        item = ThreatFeed(organization_id, data["name"], data["provider"], data.get("feed_type", "open")); self.repository.feeds[item.id] = item; return item
    def list(self, organization_id): return self.repository.list(organization_id)
    def sync(self, feed, organization_id):
        if feed.organization_id != organization_id: raise LookupError("feed_not_found")
        feed.status = "healthy"; feed.last_sync = datetime.now(timezone.utc).isoformat(); return feed
