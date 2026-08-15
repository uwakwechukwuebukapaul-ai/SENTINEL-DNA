class GovernanceDecisionRepository:
    def __init__(self): self.decisions={}; self.reviews={}
    def save(self,x): self.decisions[(x.tenant_id,x.decision_id)]=x; return x
    def get(self,tenant_id,decision_id): return self.decisions.get((tenant_id,decision_id))
    def list(self,tenant_id,status=None): return [x for (t,_),x in self.decisions.items() if t==tenant_id and (status is None or x.status==status)]
    def save_review(self,x): self.reviews[(x.tenant_id,x.decision_id)]=x; return x
    def get_review(self,tenant_id,decision_id): return self.reviews.get((tenant_id,decision_id))
