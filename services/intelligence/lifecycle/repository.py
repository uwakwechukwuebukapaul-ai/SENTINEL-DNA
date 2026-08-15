class LifecycleRepository:
    def __init__(self): self.lifecycles={}; self.decisions={}; self.approvals={}; self.actions={}; self.verifications={}; self.learning={}; self.history={}
    def save_lifecycle(self,x): self.lifecycles[(x.tenant_id,x.lifecycle_id)]=x; return x
    def get_lifecycle(self,t,i): return self.lifecycles.get((t,i))
    def save_decision(self,x): self.decisions[(x.tenant_id,x.lifecycle_id)]=x; return x
    def save_approval(self,x): self.approvals[(x.tenant_id,x.lifecycle_id)]=x; return x
    def save_action(self,t,i,x): self.actions[(t,i)]=x; return x
    def save_verification(self,x): self.verifications[(x.tenant_id,x.lifecycle_id)]=x; return x
    def save_learning(self,x): self.learning[(x.tenant_id,x.lifecycle_id)]=x; return x
    def add_history(self,t,i,event): self.history.setdefault((t,i),[]).append(event)
    def get_history(self,t,i): return list(self.history.get((t,i),[]))
