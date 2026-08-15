from .aggregation import SOCWorkspaceAggregator
from .models import SOCWorkspaceSnapshot
from .repository import WorkspaceRepository
from .context import WorkspaceContextBuilder
from .timeline import WorkspaceTimeline
from .decisions import WorkspaceDecisionSurface
from .copilot import WorkspaceCopilotContext
from .provenance import WorkspaceProvenance

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

class AnalystWorkspaceService:
    """Read-only analyst experience over existing authoritative outputs."""
    def __init__(self, repository=None, tenant_id=None, audit_logger=None, fabric=None):
        self.repository=repository or WorkspaceRepository(); self.tenant_id=tenant_id; self.audit_logger=audit_logger; self.fabric=fabric; self.context_builder=WorkspaceContextBuilder(); self.timeline=WorkspaceTimeline(); self.decisions=WorkspaceDecisionSurface(); self.copilot=WorkspaceCopilotContext(); self.provenance=WorkspaceProvenance()
    def _audit(self,event,**payload):
        if self.audit_logger and hasattr(self.audit_logger,"record"): self.audit_logger.record(event,tenant_id=self.tenant_id,**payload)
    def get_workspace(self,investigation_id,**sources):
        self._audit("analyst_workspace_retrieved",investigation_id=investigation_id); row=self.repository.get_investigation(investigation_id,self.tenant_id)
        if row is None: return None
        if self.fabric and "fabric" not in sources: sources["fabric"]=self.fabric
        context=self.context_builder.build(self.tenant_id,row,**sources); context.timeline=self.timeline.render(context.timeline); context.decisions=self.decisions.build(context.decisions); context.copilot=self.copilot.build(context); return context
    def get_timeline(self,investigation_id,**sources):
        context=self.get_workspace(investigation_id,**sources); return [] if context is None else context.timeline
    def get_evidence_view(self,investigation_id,**sources):
        context=self.get_workspace(investigation_id,**sources); return {"status":"insufficient","items":[],"requires_human_review":True} if context is None or not context.evidence else {"status":"available","items":context.evidence,"requires_human_review":True}
    def get_decision_surface(self,investigation_id,**sources):
        context=self.get_workspace(investigation_id,**sources); return [] if context is None else context.decisions
    def get_provenance(self,investigation_id,**sources):
        context=self.get_workspace(investigation_id,**sources); return [] if context is None else self.provenance.collect(context)
    def historical_workspace(self,investigation_id): return [x for x in self.repository.list(self.tenant_id) if str(x.get("investigation_id"))==str(investigation_id)]
