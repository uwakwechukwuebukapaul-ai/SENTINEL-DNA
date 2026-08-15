class WorkflowManager:
    def __init__(self, repository): self.repository=repository
    def add_action(self, action, tenant_id):
        workflow=self.repository.get_workflow(action.workflow_id, tenant_id)
        if not workflow: raise LookupError("workflow_not_found")
        return self.repository.save_action(action, tenant_id)
