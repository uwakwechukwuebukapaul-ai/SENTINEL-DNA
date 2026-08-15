class SecurityInvestmentRepository:
    def __init__(self): self.opportunities={}; self.priorities={}; self.estimates={}
    def save_opportunity(self,x): self.opportunities[(x.tenant_id,x.opportunity_id)]=x; return x
    def get_opportunity(self,i,t): return self.opportunities.get((t,i))
    def list_opportunities(self,t): return [x for (tenant,_),x in self.opportunities.items() if tenant==t]
    def save_priority(self,x): self.priorities[(x.tenant_id,x.priority_id)]=x; return x
    def save_estimate(self,x): self.estimates[(x.tenant_id,x.estimate_id)]=x; return x
