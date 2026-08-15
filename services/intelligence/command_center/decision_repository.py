class DecisionContextRepository:
    """Replaceable repository contract; all reads require tenant scope."""
    def __init__(self): self.items = {}
    def save(self, context): self.items[(context.tenant_id, context.decision_context_id)] = context; return context
    def get(self, tenant_id, decision_context_id): return self.items.get((tenant_id, str(decision_context_id)))
    def list(self, tenant_id, **filters):
        values = [v for (tenant, _), v in self.items.items() if tenant == tenant_id]
        if filters.get("attention_id"): values = [v for v in values if v.attention_id == filters["attention_id"]]
        if filters.get("investigation_reference"): values = [v for v in values if v.investigation_reference == filters["investigation_reference"]]
        return sorted(values, key=lambda v: (v.updated_at, v.decision_context_id), reverse=True)
    def get_latest(self, tenant_id):
        values = self.list(tenant_id); return values[0] if values else None
    def get_history(self, tenant_id, **filters): return self.list(tenant_id, **filters)
    def get_by_attention(self, tenant_id, attention_id): return self.list(tenant_id, attention_id=attention_id)
    def get_by_investigation(self, tenant_id, investigation_id): return self.list(tenant_id, investigation_reference=investigation_id)

