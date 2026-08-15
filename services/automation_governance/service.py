from uuid import uuid4
from datetime import datetime, timezone
from .models import AutomationWorkflow, AutomationExecution
from .repository import AutomationRepository
from .workflow import WorkflowManager
from .approvals import ApprovalManager
from .planner import AutomationPlanner
from .executor import AutomationExecutor
from .policies import AutomationPolicy
from .audit import AutomationAudit
class AutomationGovernanceService:
    def __init__(self,repository=None,audit=None):
        self.repository=repository or AutomationRepository(); self.audit=audit or AutomationAudit(); self.workflow=WorkflowManager(self.repository); self.approvals=ApprovalManager(self.repository); self.planner=AutomationPlanner(); self.executor=AutomationExecutor(); self.policy=AutomationPolicy()
    def create_workflow(self,tenant_id,name,description="",workflow_id=None):
        workflow=AutomationWorkflow(workflow_id or str(uuid4()),tenant_id,name,description); self.repository.save_workflow(workflow); self.audit.record("workflow_created",tenant_id=tenant_id,workflow_id=workflow.workflow_id); return workflow
    def add_action(self,tenant_id,action):
        if not self.policy.allows(action): raise PermissionError("action_not_allowed")
        action.requires_approval=self.policy.requires_approval(action); return self.workflow.add_action(action,tenant_id)
    def request_execution(self,tenant_id,workflow_id,requester):
        workflow=self.repository.get_workflow(workflow_id,tenant_id)
        if not workflow: raise LookupError("workflow_not_found")
        execution=AutomationExecution(str(uuid4()),workflow_id,tenant_id); self.repository.save_execution(execution); approval=self.approvals.request(execution,requester); self.audit.record("approval_requested",tenant_id=tenant_id,execution_id=execution.execution_id); return execution,approval
    def approve_and_execute(self,tenant_id,execution_id,approval_id,approver,decision="APPROVED",reason=""):
        approval=self.approvals.decide(approval_id,tenant_id,approver,decision,reason); execution=self.repository.get_execution(execution_id,tenant_id)
        if not execution or approval.execution_id != execution_id: raise LookupError("execution_not_found")
        if approval.decision != "APPROVED": execution.status="REJECTED"; return execution
        actions=self.repository.list_actions(execution.workflow_id,tenant_id); execution.status="RUNNING"; workflow=self.repository.get_workflow(execution.workflow_id,tenant_id)
        try: execution.result={"simulation":True,"results":self.executor.execute(self.planner.plan(workflow,actions))}; execution.status="SUCCESS"
        except Exception as exc: execution.status="FAILED"; execution.error_message=str(exc)
        execution.completed_at=datetime.now(timezone.utc).isoformat(); self.audit.record("workflow_simulated",tenant_id=tenant_id,execution_id=execution_id,approver=approver); return execution
