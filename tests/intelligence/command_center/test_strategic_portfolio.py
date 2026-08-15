from services.intelligence.command_center.strategic_portfolio_service import StrategicPortfolioService
class Strategy:
    def derive(self,t): return {"tenant_id":t,"strategic_signals":[{"tenant_id":t,"signal_id":"s1","current_state":"degrading","organizational_dimension":"detection","priority":"high","score":42,"confidence":"medium","evidence_strength":"moderate","uncertainty":[],"provenance":{"source":"strategy"},"contributing_references":["r1"]}]}
class Analytics:
    def derive(self,t): return {"effectiveness":[{"classification":"insufficient_evidence"}]}
def test_portfolio_is_deterministic_bounded_and_advisory():
    s=StrategicPortfolioService(Strategy(),Analytics()); a=s.derive("a"); assert a==s.derive("a"); assert a["portfolio_score"] is not None and 0<=a["portfolio_score"]<=100; assert a["portfolio_status"]=="degrading"; assert a["advisory_only"] is True
def test_portfolio_tenant_and_missing_signal():
    s=StrategicPortfolioService(Strategy(),Analytics()); assert s.derive("b")["tenant_id"]=="b"; assert s.detail("a","missing") is None
