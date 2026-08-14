from datetime import datetime, timezone
from uuid import uuid4
from .models import ApprovalRequest

class ApprovalEngine:
    def request(self, tenant_id, plan_id, requester): return ApprovalRequest(str(uuid4()), tenant_id, plan_id, requester)
    def decide(self, request, approver, decision):
        request.approver=approver; request.decision=decision; request.decided_at=datetime.now(timezone.utc).isoformat(); return request
