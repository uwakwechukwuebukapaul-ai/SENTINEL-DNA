from services.intelligence.command_center.strategic_planning_analytics_service import StrategicPlanningAnalyticsService
class Planning:
    def derive(self,tenant): return {"tenant_id":tenant,"planning":{"planning_status":"insufficient_history","historical_evidence_quality":"insufficient_history"},"priorities":[{"stable_id":"p1","title":"Regression","dimension":"detection","classification":"unresolved_priority","confidence":"low","evidence_strength":"limited","uncertainty":[],"provenance":{"source":"planning"},"contributing_references":["r1"]}]}
def test_analytics_is_deterministic_and_advisory():
    s=StrategicPlanningAnalyticsService(Planning()); a=s.derive("a"); assert a==s.derive("a"); assert a["priority_lifecycles"][0]["classification"]=="insufficient_history"; assert a["advisory_only"] is True; assert "causation" in a["effectiveness"][0]["interpretation"]
def test_tenant_and_missing_signal():
    s=StrategicPlanningAnalyticsService(Planning()); assert s.derive("b")["tenant_id"]=="b"; assert s.detail("a","missing") is None
