class InvestigationQualityRepository:
    def __init__(self): self._items={}
    def save_assessment(self, assessment): self._items[(assessment.tenant_id,assessment.investigation_id)]=assessment; return assessment
    def get_assessment(self, tenant_id, investigation_id): return self._items.get((tenant_id,investigation_id))
    def list_assessments(self, tenant_id): return [item for (item_tenant,_),item in self._items.items() if item_tenant==tenant_id]
