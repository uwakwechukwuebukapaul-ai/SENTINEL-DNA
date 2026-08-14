class PilotReportService:
    def security_posture(self, organization_id, analytics, compliance=None): return {"organization_id": organization_id, "security_posture": "pilot_assessment", "analytics": analytics, "compliance": compliance or {}}
    def incident_summary(self, organization_id, incidents): return {"organization_id": organization_id, "incident_count": len(incidents), "incidents": incidents}
    def roi(self, organization_id, analytics): return {"organization_id": organization_id, "analyst_actions_avoided": analytics.get("automation_impact", 0), "response_improvement": analytics.get("MTTR", 0)}
    def generate(self, organization_id, analytics, incidents=None, compliance=None): return {"security_posture": self.security_posture(organization_id, analytics, compliance), "incident_summary": self.incident_summary(organization_id, incidents or []), "roi_metrics": self.roi(organization_id, analytics)}
