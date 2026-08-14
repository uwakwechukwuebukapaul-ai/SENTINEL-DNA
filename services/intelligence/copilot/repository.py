class CopilotRepository:
    def __init__(self): self._history={}
    def append(self, tenant_id, item): self._history.setdefault(tenant_id, []).append(item); return item
    def history(self, tenant_id): return list(self._history.get(tenant_id, []))
