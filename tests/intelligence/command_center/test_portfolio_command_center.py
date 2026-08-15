from services.intelligence.command_center.portfolio_command_center_service import PortfolioCommandCenterService
class Portfolio:
    def derive(self,t): return {"portfolio":[{"tenant_id":t,"signal_id":"s1","priority_id":"p1","dimension":"detection","lifecycle_state":"degrading","portfolio_status":"degrading","priority":"high","score":40,"confidence":"medium","evidence_strength":"moderate","uncertainty":[],"provenance":{"source":"portfolio"},"contributing_references":["r1"]}]}
class Strategy:
    def derive(self,t): return {"tenant_id":t,"strategic_signals":[]}
class Analytics:
    def derive(self,t): return {"effectiveness":[]}
def test_command_center_is_deterministic_bounded_and_advisory():
    s=PortfolioCommandCenterService(Portfolio(),Strategy(),Analytics()); a=s.derive("a"); assert a==s.derive("a"); assert 0<=a["portfolio_health_score"]<=100; assert a["portfolio_status"]=="at_risk"; assert a["advisory_only"] is True
def test_tenant_and_unknown_signal():
    s=PortfolioCommandCenterService(Portfolio(),Strategy(),Analytics()); assert s.derive("b")["tenant_id"]=="b"; assert s.detail("a","missing") is None
