class CustomerSuccessService:
    def __init__(self): self.data = {}
    def record(self, organization_id, metric, value=1): self.data.setdefault(organization_id, {}).setdefault(metric, 0); self.data[organization_id][metric] += value; return self.data[organization_id]
    def report(self, organization_id): return {"organization_id": organization_id, "incidents_handled": 0, "response_improvement": 0, "ai_accuracy": 0, "analyst_productivity": 0, "soc_maturity_improvement": 0, **self.data.get(organization_id, {})}
