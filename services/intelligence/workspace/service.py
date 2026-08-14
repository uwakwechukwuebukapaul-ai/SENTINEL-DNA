from .aggregation import SOCWorkspaceAggregator
from .models import SOCWorkspaceSnapshot
from .repository import WorkspaceRepository

class SOCWorkspaceService:
    """Read-only workspace contract for future API routes."""
    def __init__(self, repository=None, tenant_id=None, audit_logger=None, components=None): self.repository=repository or WorkspaceRepository(); self.tenant_id=tenant_id; self.audit_logger=audit_logger; self.aggregator=SOCWorkspaceAggregator(components)
    def _audit(self, event, **payload):
        if self.audit_logger and hasattr(self.audit_logger, "record"): self.audit_logger.record(event, tenant_id=self.tenant_id, **payload)
    def get_investigation_workspace(self, investigation_id):
        self._audit("workspace_investigation_viewed", investigation_id=investigation_id); row=self.repository.get_investigation(investigation_id, self.tenant_id); return self.aggregator.snapshot(investigation_id, result=row) if row else None
    def get_case_workspace(self, case_id):
        self._audit("workspace_case_viewed", case_id=case_id); row=self.repository.get_case(case_id, self.tenant_id); return self.aggregator.case_view(case_id, row, self.tenant_id) if row else None
    def get_threat_overview(self): return {"tenant_id": self.tenant_id, "investigations": len(self.repository.list(self.tenant_id))}
    def get_detection_overview(self): return {"tenant_id": self.tenant_id, "available": True}
    def get_security_posture(self): return {"tenant_id": self.tenant_id, "availability": "partial", "status": "unknown"}
