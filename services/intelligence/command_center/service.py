from .aggregation import SOCCommandCenterAggregator
from .repository import CommandCenterRepository

class SOCCommandCenterService:
    """Read-only analyst/executive command-center experience contract."""
    def __init__(self, repository=None, tenant_id=None, audit_logger=None, components=None): self.repository=repository or CommandCenterRepository(); self.tenant_id=tenant_id; self.audit_logger=audit_logger; self.aggregator=SOCCommandCenterAggregator(components)
    def _snapshot(self):
        rows=self.repository.list_investigations(self.tenant_id); decisions=self.repository.list_decisions(self.tenant_id)
        if self.audit_logger and hasattr(self.audit_logger, "record"): self.audit_logger.record("command_center_snapshot_viewed", tenant_id=self.tenant_id)
        return self.aggregator.aggregate(self.tenant_id, rows, decisions)
    def get_snapshot(self): return self._snapshot()
    def get_investigation_overview(self): return self._snapshot().investigations
    def get_posture_summary(self): return self._snapshot().executive_posture
    def get_pending_decisions(self): return self._snapshot().pending_decisions
