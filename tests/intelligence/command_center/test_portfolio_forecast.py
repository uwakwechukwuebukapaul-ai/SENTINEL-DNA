from services.intelligence.command_center.portfolio_forecast_service import PortfolioForecastService
class Command:
    def derive(self,t): return {"portfolio_status":"healthy","provenance":["portfolio"],"signals":[{"signal_id":"s1","title":"Progress","state":"improving","category":"opportunity","dimension":"detection","score":70,"confidence":"medium","evidence_strength":"moderate","uncertainty":[],"contributing_references":[]}]}
def test_forecast_is_deterministic_bounded_and_advisory():
    s=PortfolioForecastService(Command()); a=s.derive("a"); assert a==s.derive("a"); assert 0<=a["forecast"]["portfolio_health_score"]<=100; assert a["forecast"]["projected_trajectory"]=="improving"; assert a["advisory_only"] is True; assert "guaranteed" in a["projected_opportunities"][0]["projection"]
def test_forecast_tenant_and_missing_signal():
    s=PortfolioForecastService(Command()); assert s.derive("b")["tenant_id"]=="b"; assert s.detail("a","missing") is None
