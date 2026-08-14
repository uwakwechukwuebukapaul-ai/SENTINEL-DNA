from .approval import ApprovalEngine
from .executor import SimulationExecutor
from .planner import ResponsePlanner
from .repository import ResponseRepository

class IncidentResponseService:
    def __init__(self, tenant_id=None, repository=None, audit_logger=None): self.tenant_id=tenant_id; self.repository=repository or ResponseRepository(); self.audit_logger=audit_logger; self.planner=ResponsePlanner(); self.approval=ApprovalEngine(); self.executor=SimulationExecutor()
    def _audit(self, event, **payload):
        if self.audit_logger and hasattr(self.audit_logger, "record"): self.audit_logger.record(event, tenant_id=self.tenant_id, **payload)
    def create_plan(self, investigation=None, risk_score=0.0, threat_classification=None, correlation=None, attack_paths=None):
        plan=self.repository.save_plan(self.planner.create(self.tenant_id, investigation, risk_score, threat_classification, correlation, attack_paths)); self._audit("response_plan_created", plan_id=plan.plan_id); return plan
    def request_approval(self, plan_id, requester):
        if self.repository.get_plan(self.tenant_id, plan_id) is None: return None
        request=self.repository.save_approval(self.approval.request(self.tenant_id, plan_id, requester)); self._audit("response_approval_requested", plan_id=plan_id, request_id=request.request_id); return request
    def approve(self, request_id, approver, decision="approved"):
        request=self.repository.get_approval(self.tenant_id, request_id)
        if request is None: return None
        request=self.approval.decide(request, approver, decision); self._audit("response_approval_decided", request_id=request_id, decision=decision, approver=approver); return request
    def execute(self, plan_id, request_id):
        plan=self.repository.get_plan(self.tenant_id, plan_id); approval=self.repository.get_approval(self.tenant_id, request_id) if request_id else None
        result=self.repository.save_execution(self.executor.execute(plan, approval)) if plan else None; self._audit("response_execution_simulated", plan_id=plan_id, status=result.status if result else "missing"); return result
