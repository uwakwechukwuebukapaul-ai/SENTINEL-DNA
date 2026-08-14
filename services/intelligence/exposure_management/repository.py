class ExposureRepository:
    def __init__(self): self._items={}
    def save(self, exposure): self._items[(exposure.tenant_id, exposure.exposure_id)]=exposure; return exposure
    def list(self, tenant_id): return [item for (item_tenant, _), item in self._items.items() if item_tenant == tenant_id]
