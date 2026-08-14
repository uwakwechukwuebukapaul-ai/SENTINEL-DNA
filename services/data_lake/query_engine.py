class SecurityQueryEngine:
    def __init__(self, repository): self.repository = repository
    def search(self, organization_id, filters=None):
        events = self.repository.query(organization_id, filters)
        return {"events": [e.public() for e in events], "count": len(events), "related_incidents": [], "related_investigations": [], "related_indicators": sorted({i for e in events for i in e.ioc_matches})}
