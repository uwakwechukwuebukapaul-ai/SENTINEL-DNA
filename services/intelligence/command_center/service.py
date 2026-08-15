from .aggregation import SOCCommandCenterAggregator
from .repository import CommandCenterRepository

class SOCCommandCenterService:
    """Presentation orchestration over the existing Command Surface and domain owners."""
    def __init__(self, repository=None, tenant_id=None, audit_logger=None, components=None): self.repository=repository or CommandCenterRepository(); self.tenant_id=tenant_id; self.audit_logger=audit_logger; self.aggregator=SOCCommandCenterAggregator(components)
    def _snapshot(self):
        rows=self.repository.list_investigations(self.tenant_id); decisions=self.repository.list_decisions(self.tenant_id)
        if self.audit_logger and hasattr(self.audit_logger, "record"): self.audit_logger.record("command_center_snapshot_viewed", tenant_id=self.tenant_id)
        return self.aggregator.aggregate(self.tenant_id, rows, decisions)
    def get_snapshot(self): return self._snapshot()
    def get_investigation_overview(self): return self._snapshot().investigations
    def get_posture_summary(self): return self._snapshot().executive_posture
    def get_pending_decisions(self): return self._snapshot().pending_decisions

class CommandCenterPresentationService:
    def __init__(self, command_surface=None, audit=None): self.command_surface=command_surface; self.audit=audit
    def build_context(self, tenant_id, sources=None):
        from .context import ContextNormalizer
        from .models import SOCCommandSnapshot
        data=ContextNormalizer().build(tenant_id, sources or {}); data["tenant_id"]=tenant_id
        if self.command_surface:
            snap=self.command_surface.build_snapshot(tenant_id, sources or {}); data["attention"]=[x.to_dict() for x in snap.attention_items]; data["decisions"]=[x.to_dict() for x in snap.decision_items]
        if self.audit and hasattr(self.audit,"record"): self.audit.record("command_center_context", tenant_id=tenant_id)
        return {**data, "advisory":True, "requires_human_review":True, "copilot_context":{"tenant_id":tenant_id,"tts_enabled":False}}
    def get_attention(self, tenant_id, sources=None): return self.build_context(tenant_id,sources).get("attention",[])
    def get_investigations(self, tenant_id, sources=None): return self.build_context(tenant_id,sources).get("investigations",[])
    def get_evidence(self, tenant_id, sources=None): return self.build_context(tenant_id,sources).get("evidence",[])
    def get_decisions(self, tenant_id, sources=None): return self.build_context(tenant_id,sources).get("decisions",[])
    def get_executive(self, tenant_id, sources=None): return self.build_context(tenant_id,sources).get("executive",{})
    def get_subsystems(self, tenant_id, sources=None): return self.build_context(tenant_id,sources).get("subsystem_availability",{})
