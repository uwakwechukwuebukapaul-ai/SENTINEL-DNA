from .models import AutomationPerformance
class PerformanceEngine:
    def calculate(self, tenant_id, workflow_id, experiences):
        n=len(experiences); successes=sum(x.outcome.lower() in {"success","successful"} for x in experiences); approvals=sum(x.approval_decision.upper()=="APPROVED" for x in experiences)
        return AutomationPerformance(workflow_id,tenant_id,n,successes,approvals,n-approvals,round(successes/n,3) if n else 0.0,round(approvals/n,3) if n else 0.0,round(min(1.0,(n/10))*((successes/n) if n else 0),3))
