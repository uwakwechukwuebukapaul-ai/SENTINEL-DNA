from services.intelligence.command_center.forecast_accuracy_service import ForecastAccuracyService
class Forecast:
    def derive(self,t): return {"projected_opportunities":[{"signal_id":"s1","direction":"improving","score":70,"confidence":"medium","evidence_strength":"moderate","uncertainty":[],"provenance":["forecast"]}],"projected_risks":[]}
class Portfolio:
    def derive(self,t): return {"signals":[{"tenant_id":t,"signal_id":"s1","state":"improving","score":68}]}
def test_accuracy_is_deterministic_and_bounded():
    s=ForecastAccuracyService(Forecast(),Portfolio()); a=s.derive("a"); assert a==s.derive("a"); assert 0<=a["reliability_score"]<=100; assert a["forecast_evaluations"][0]["alignment"]=="aligned"; assert a["advisory_only"] is True
def test_accuracy_tenant_and_missing_signal():
    s=ForecastAccuracyService(Forecast(),Portfolio()); assert s.derive("b")["tenant_id"]=="b"; assert s.detail("a","missing") is None
