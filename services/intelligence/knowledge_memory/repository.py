class KnowledgeMemoryRepository:
    def __init__(self): self._records={}
    def save(self, record): self._records.setdefault(record.tenant_id, []).append(record); return record
    def list(self, tenant_id): return list(self._records.get(tenant_id, []))
