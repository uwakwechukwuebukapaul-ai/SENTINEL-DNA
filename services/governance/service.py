from datetime import datetime, timezone
from uuid import uuid4
class GovernanceService:
    def __init__(self,repository=None):
        self.records = []; self.approvals = {}; self.usage = []
        from .repository import PolicyRepository
        from .evaluator import PolicyEvaluator
        from .defaults import DEFAULT_POLICIES
        from .audit import GovernanceAuditLogger
        self.repository=repository or PolicyRepository(); [self.repository.create_policy(p) for p in DEFAULT_POLICIES if not self.repository.get_policy(p.policy_id)]; self.evaluator=PolicyEvaluator(self.repository); self.audit=GovernanceAuditLogger()
    def evaluate_ai_request(self,tenant_id,request): return self.evaluator.evaluate(tenant_id,"ai",request)
    def evaluate_investigation_access(self,tenant_id,request): return self.evaluator.evaluate(tenant_id,"investigation",request)
    def evaluate_soar_action(self,tenant_id,request): return self.evaluator.evaluate(tenant_id,"automation",request)
    def evaluate_integration_action(self,tenant_id,request): return self.evaluator.evaluate(tenant_id,"integration",request)
    def create_policy(self,policy): self.audit.record("policy_created",policy_id=policy.policy_id); return self.repository.create_policy(policy)
    def audit_decision(self, organization_id, decision, prompt=None, model="deterministic", confidence=None):
        item = {"id": str(uuid4()), "organization_id": organization_id, "decision": decision, "prompt": prompt, "model": model, "confidence": confidence, "created_at": datetime.now(timezone.utc).isoformat()}; self.records.append(item); self.usage.append({"organization_id": organization_id, "model": model}); return item
    def request_approval(self, organization_id, action, decision_id):
        item = {"id": str(uuid4()), "organization_id": organization_id, "action": action, "decision_id": decision_id, "status": "pending"}; self.approvals[item["id"]] = item; return item
    def approve(self, approval_id, status):
        if status not in {"approved", "rejected"} or approval_id not in self.approvals: raise ValueError("invalid_approval")
        self.approvals[approval_id]["status"] = status; return self.approvals[approval_id]
    def restricted(self, action): return action in {"delete_evidence", "disable_detection", "isolate_production"}
