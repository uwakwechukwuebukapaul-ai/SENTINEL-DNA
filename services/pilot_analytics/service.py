class PilotAnalyticsService:
    def __init__(self): self.records = {}
    def record(self, organization_id, metric, value=1): self.records.setdefault(organization_id, {}).setdefault(metric, 0); self.records[organization_id][metric] += value; return self.records[organization_id]
    def report(self, organization_id):
        data = self.records.get(organization_id, {}); return {"organization_id": organization_id, "MTTD": data.get("mttd_ms", 0), "MTTR": data.get("mttr_ms", 0), "investigation_duration": data.get("investigation_duration_ms", 0), "analyst_actions": data.get("analyst_actions", 0), "ai_accuracy": data.get("ai_accuracy", 0), "automation_impact": data.get("automation_impact", 0)}
