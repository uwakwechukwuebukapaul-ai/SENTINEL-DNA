class InvestigationOptimizationRepository:
    def __init__(self): self._results={}
    def save(self, result, plan_id): self._results[(result.tenant_id, plan_id)]=result; return result
    def list(self, tenant_id): return [result for (item_tenant,_), result in self._results.items() if item_tenant == tenant_id]
