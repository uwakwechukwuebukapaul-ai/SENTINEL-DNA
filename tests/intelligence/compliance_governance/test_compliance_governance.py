from services.intelligence.compliance_governance import *
def test_assessment_coverage_and_gaps():
    s=ComplianceGovernanceService(); s.register_framework(Framework("f","t1","NIST")); s.register_control(Control("c1","f","t1","Logging",status="implemented",evidence_refs=["e"])); s.register_control(Control("c2","f","t1","Review")); a=s.assess("t1","f"); assert a.score==50 and s.coverage_score("t1","f")==.5; assert s.identify_gaps("t1","f")[0].requires_human_review
def test_tenant_isolation():
    s=ComplianceGovernanceService(); s.register_framework(Framework("f","t1","X")); s.register_control(Control("c","f","t1","C",status="implemented")); assert s.assess("t2","f").assessed_controls==0 and s.identify_gaps("t2","f")==[]
