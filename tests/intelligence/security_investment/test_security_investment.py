from services.intelligence.security_investment import *
def test_prioritization_and_reduction():
    s=SecurityInvestmentService(); x=SecurityImprovementOpportunity("o","t1","Improve detection","detection",current_control_effectiveness=.2); s.register_opportunity(x); p=s.prioritize("t1",{"o":90},{"o":80}); assert p[0].requires_human_review; e=s.estimate_reduction("t1","o",90); assert e.reduction>0
def test_tenant_isolation():
    s=SecurityInvestmentService(); s.register_opportunity(SecurityImprovementOpportunity("o","t1","x","x")); assert s.summary("t2")["opportunity_count"]==0 and s.estimate_reduction("t2","o",90) is None
