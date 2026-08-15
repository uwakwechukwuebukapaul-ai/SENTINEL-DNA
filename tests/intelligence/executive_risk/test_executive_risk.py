from services.intelligence.executive_risk import *
def test_business_risk_and_tenant_isolation():
    s=ExecutiveRiskService(); a=BusinessAsset("a","t1","Payments","business_application",business_value=100,revenue_impact=100,operational_impact=80,regulatory_impact=90); s.register_asset(a); assessment=s.assess_asset("t1","a",security_risk=90,exposure=80); assert assessment.risk_level=="critical"; assert s.assess_asset("t2","a") is None; assert s.recommendations_for("t1","a",security_risk=90)
def test_empty_summary(): assert ExecutiveRiskService().summary("empty")["asset_count"]==0
