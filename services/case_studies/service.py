class CaseStudyService:
    def generate(self, organization_id, incident, before=None, after=None, analyst_impact=None):
        return {"organization_id": organization_id, "incident_summary": incident, "before_metrics": before or {}, "after_metrics": after or {}, "analyst_impact": analyst_impact or {}, "executive_report": f"Security exercise for {organization_id}: incident workflow completed with measurable operational outcomes."}
