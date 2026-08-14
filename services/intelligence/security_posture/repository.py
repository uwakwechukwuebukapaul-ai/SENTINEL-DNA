class SecurityPostureRepository:
    def __init__(self): self._items={}
    def save(self, posture): self._items[posture.tenant_id]=posture; return posture
    def get(self, tenant_id): return self._items.get(tenant_id)
