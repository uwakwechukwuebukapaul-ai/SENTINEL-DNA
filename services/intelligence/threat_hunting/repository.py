class ThreatHuntingRepository:
    def __init__(self): self.hypotheses={}; self.queries={}; self.results={}
    def save_hypothesis(self, item): self.hypotheses[(item.tenant_id,item.hypothesis_id)]=item; return item
    def save_query(self, item): self.queries[(item.tenant_id,item.query_id)]=item; return item
    def save_result(self, item): self.results[(item.tenant_id,item.query_id)]=item; return item
    def get_query(self, tenant_id, query_id): return self.queries.get((tenant_id,query_id))
