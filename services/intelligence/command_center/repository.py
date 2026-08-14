class CommandCenterRepository:
    """Tenant-scoped read/storage abstraction for command-center projections."""
    def __init__(self, investigations=None, decisions=None):
        self._investigations = list(investigations or [])
        self._decisions = list(decisions or [])
    def list_investigations(self, tenant_id=None): return [x for x in self._investigations if tenant_id is None or x.get("tenant_id") == tenant_id]
    def list_decisions(self, tenant_id=None): return [x for x in self._decisions if (tenant_id is None or x.get("tenant_id") == tenant_id) and x.get("status", "pending") == "pending"]
