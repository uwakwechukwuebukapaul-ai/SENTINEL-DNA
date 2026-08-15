class AutomationRepository:
    def __init__(self): self.workflows={}; self.actions={}; self.executions={}; self.approvals={}
    def save_workflow(self, x): self.workflows[(x.tenant_id,x.workflow_id)]=x; return x
    def get_workflow(self, i, t): return self.workflows.get((t,i))
    def list_workflows(self,t): return [x for (tenant,_),x in self.workflows.items() if tenant==t]
    def save_action(self,x,t): self.actions[(t,x.action_id)]=x; return x
    def list_actions(self,w,t): return [x for (tenant,_),x in self.actions.items() if tenant==t and x.workflow_id==w]
    def save_execution(self,x): self.executions[(x.tenant_id,x.execution_id)]=x; return x
    def get_execution(self,i,t): return self.executions.get((t,i))
    def save_approval(self,x): self.approvals[(x.tenant_id,x.approval_id)]=x; return x
    def get_approval(self,i,t): return self.approvals.get((t,i))
