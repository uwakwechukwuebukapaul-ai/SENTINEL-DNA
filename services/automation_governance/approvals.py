from uuid import uuid4
class ApprovalManager:
    def __init__(self, repository): self.repository=repository
    def request(self, execution, requester): return self.repository.save_approval(__import__('services.automation_governance.models', fromlist=['ApprovalRecord']).ApprovalRecord(str(uuid4()), execution.execution_id, execution.tenant_id, requester))
    def decide(self, approval_id, tenant_id, approver, decision, reason=""):
        record=self.repository.get_approval(approval_id, tenant_id)
        if not record: raise LookupError("approval_not_found")
        if decision not in {"APPROVED", "REJECTED"}: raise ValueError("invalid_approval_decision")
        record.approver, record.decision, record.reason = approver, decision, reason; return record
