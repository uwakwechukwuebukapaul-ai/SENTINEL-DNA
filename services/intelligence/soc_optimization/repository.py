class OptimizationRepository:
    def __init__(self): self.items={}
    def save(self,x): self.items[(x.tenant_id,x.candidate_id)]=x; return x
    def list(self,tenant_id,domain=None,priority=None): return [x for (t,_),x in self.items.items() if t==tenant_id and (domain is None or x.domain==domain) and (priority is None or x.priority==priority)]
