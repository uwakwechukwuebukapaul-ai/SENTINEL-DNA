class SecurityAnalyticsRepository:
    def __init__(self): self._items={}
    def save(self, snapshot): self._items.setdefault(snapshot.tenant_id, []).append(snapshot); return snapshot
    def list(self, tenant_id): return list(self._items.get(tenant_id, []))
