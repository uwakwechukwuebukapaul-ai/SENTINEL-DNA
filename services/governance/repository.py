class PolicyRepository:
    def __init__(self): self.policies={}
    def create_policy(self,p): self.policies[p.policy_id]=p; return p
    def get_policy(self,i): return self.policies.get(i)
    def list_policies(self,tenant_id=None): return [p for p in self.policies.values() if tenant_id is None or p.tenant_id==tenant_id]
    def update_policy(self,i,**changes): p=self.policies[i]; [setattr(p,k,v) for k,v in changes.items() if hasattr(p,k)]; return p
    def disable_policy(self,i): return self.update_policy(i,enabled=False)
    def delete_policy(self,i): return self.policies.pop(i,None) is not None
