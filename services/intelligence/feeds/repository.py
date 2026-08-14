class ThreatFeedRepository:
    def __init__(self): self.feeds = {}
    def list(self, organization_id): return [x for x in self.feeds.values() if x.organization_id == organization_id]
