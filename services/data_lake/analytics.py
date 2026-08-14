from collections import Counter

class AnalyticsService:
    def __init__(self, repository): self.repository = repository
    def _events(self, organization_id): return self.repository.list(organization_id)
    def threat_trends(self, organization_id): return dict(Counter(e.severity for e in self._events(organization_id)))
    def techniques(self, organization_id): return dict(Counter(t for e in self._events(organization_id) for t in e.mitre_mapping))
    def assets(self, organization_id): return dict(Counter(e.asset_id for e in self._events(organization_id) if e.asset_id))
    def summary(self, organization_id): return {"events_stored": len(self._events(organization_id)), "threat_trends": self.threat_trends(organization_id), "techniques": self.techniques(organization_id), "top_assets": self.assets(organization_id), "top_users": dict(Counter(e.user_id for e in self._events(organization_id) if e.user_id)), "ioc_activity": dict(Counter(i for e in self._events(organization_id) for i in e.ioc_matches))}
