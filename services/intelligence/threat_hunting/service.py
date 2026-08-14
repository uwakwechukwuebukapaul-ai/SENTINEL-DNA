from .hunter import HuntingEngine
from .hypothesis import HypothesisEngine
from .queries import generate_queries
from .repository import ThreatHuntingRepository

class ThreatHuntingService:
    def __init__(self, tenant_id=None, repository=None): self.tenant_id=tenant_id; self.repository=repository or ThreatHuntingRepository(); self.hypotheses=HypothesisEngine(); self.hunter=HuntingEngine()
    def create_hypothesis(self, **sources): return self.repository.save_hypothesis(self.hypotheses.create(self.tenant_id, **sources))
    def generate_queries(self, hypothesis): return [self.repository.save_query(query) for query in generate_queries(hypothesis)]
    def execute_hunt(self, query, context=None):
        if query.tenant_id != self.tenant_id: return None
        return self.repository.save_result(self.hunter.execute(query, context))
    def collect_results(self, query_id):
        query=self.repository.get_query(self.tenant_id, query_id); return self.repository.results.get((self.tenant_id, query_id)) if query else None
