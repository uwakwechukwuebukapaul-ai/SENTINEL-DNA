from .models import SOARApproval
class ApprovalEngine:
    def __init__(self,repository): self.repository=repository
    def request_approval(self,eid): return self.repository.save_approval(SOARApproval("APR-"+eid,eid))
    def approve(self,eid,who,notes=""): a=self.repository.approvals.get("APR-"+eid); a.status="approved"; a.approved_by=who; a.notes=notes; return a
    def reject(self,eid,who,notes=""): a=self.repository.approvals.get("APR-"+eid); a.status="rejected"; a.approved_by=who; a.notes=notes; return a
    def get_status(self,eid): return self.repository.approvals.get("APR-"+eid)
