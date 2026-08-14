from services.compliance import ComplianceService,ComplianceFramework,SecurityControl
def test_framework_models(): assert ComplianceFramework("N","N").to_dict()["name"]=="N"
def test_control_serialization(): assert "control_id" in SecurityControl("c","f","C").to_dict()
def test_control_assessment(): assert ComplianceService().assess_framework("t")
def test_nist_mapping(): assert ComplianceService().default_controls[0].framework_id=="NIST_CSF"
def test_mitre_mapping(): assert any(x.framework_id=="MITRE" for x in ComplianceService().default_controls)
def test_compliance_evaluation(): assert ComplianceService().assess_framework("t",capabilities=["telemetry"])[0].status=="implemented"
def test_gap_detection(): assert ComplianceService().get_security_posture("t").score > 0
def test_risk_scoring(): assert ComplianceService().risk_engine.calculate("t",threat_score=100).severity=="high"
def test_tenant_isolation():
 s=ComplianceService(); s.assess_framework("a"); assert s.get_control_status("b") == []
def test_dashboard_summary(): assert ComplianceService().get_security_posture("t").to_dict()["tenant_id"]=="t"
def test_backward_compatibility(): assert ComplianceService().summary("x")["controls"]==0
