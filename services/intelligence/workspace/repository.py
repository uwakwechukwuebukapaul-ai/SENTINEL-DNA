class WorkspaceRepository:
    """Authorization-ready read boundary; records are explicitly tenant-scoped."""
    def __init__(self, records=None): self._records = list(records or [])
    def get_investigation(self, investigation_id, tenant_id=None):
        return next((item for item in self._records if str(item.get("investigation_id")) == str(investigation_id) and (tenant_id is None or item.get("tenant_id") == tenant_id)), None)
    def get_case(self, case_id, tenant_id=None):
        return next((item for item in self._records if str(item.get("case_id")) == str(case_id) and (tenant_id is None or item.get("tenant_id") == tenant_id)), None)
    def list(self, tenant_id=None): return [item for item in self._records if tenant_id is None or item.get("tenant_id") == tenant_id]
