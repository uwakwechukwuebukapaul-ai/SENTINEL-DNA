class ResponseRepository:
    def __init__(self): self.plans={}; self.approvals={}; self.executions={}
    def save_plan(self, plan): self.plans[(plan.tenant_id, plan.plan_id)]=plan; return plan
    def get_plan(self, tenant_id, plan_id): return self.plans.get((tenant_id, plan_id))
    def save_approval(self, approval): self.approvals[(approval.tenant_id, approval.request_id)]=approval; return approval
    def get_approval(self, tenant_id, request_id): return self.approvals.get((tenant_id, request_id))
    def save_execution(self, execution): self.executions[(execution.tenant_id, execution.execution_id)]=execution; return execution
