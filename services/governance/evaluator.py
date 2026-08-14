from .models import PolicyDecision
class PolicyEvaluator:
    def __init__(self,repository): self.repository=repository
    def evaluate(self,tenant_id,category,request):
        for p in self.repository.list_policies(tenant_id)+self.repository.list_policies("default"):
            if p.enabled and p.category==category:
                if category=="ai" and request.get("execute_actions"): return PolicyDecision(False,"ai_actions_restricted",p.policy_id)
                if category=="automation" and request.get("destructive"): return PolicyDecision(False,"destructive_action_blocked",p.policy_id)
                if request.get("external") and p.rules.get("external_actions_require_approval"): return PolicyDecision(False,"approval_required",p.policy_id)
                if request.get("expose_credentials"): return PolicyDecision(False,"credentials_protected",p.policy_id)
        return PolicyDecision(True,"allowed",metadata={"tenant_id":tenant_id})
    def check_permission(self,*args,**kwargs): return self.evaluate(*args,**kwargs)
    def check_action(self,*args,**kwargs): return self.evaluate(*args,**kwargs)
