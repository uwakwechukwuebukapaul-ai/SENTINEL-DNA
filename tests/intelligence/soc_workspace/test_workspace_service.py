from services.intelligence.soc_workspace import SOCWorkspaceService

def rows(): return [{"case_id":"C-1","status":"completed","risk":{"severity":"high"},"confidence":.9,"mitre":["T1566"],"threat_intelligence_report":{"threat_score":80,"matched_indicators":[]},"reasoning_report":{"summary":"x"},"decision_report":{"verdict":"true_positive"}}]
def test_workspace_snapshot(): assert SOCWorkspaceService(cases=rows()).get_workspace_snapshot().active_cases == 1
def test_case_workspace_view(): assert SOCWorkspaceService(cases=rows()).get_case_workspace("C-1").case_id == "C-1"
def test_risk_metrics(): assert SOCWorkspaceService(cases=rows()).get_investigation_metrics()["risk_distribution"]["high"] == 1
def test_ai_metrics(): assert SOCWorkspaceService(cases=rows()).get_investigation_metrics()["ai"]["average_confidence"] == .9
def test_threat_posture(): assert SOCWorkspaceService(cases=rows()).get_threat_posture().threat_score_average == 80
def test_partial_component_failure(): assert SOCWorkspaceService(cases=[{"case_id":"C-2","risk":"low"}]).get_case_workspace("C-2").case_id == "C-2"
def test_serialization(): assert "generated_at" in SOCWorkspaceService(cases=rows()).get_workspace_snapshot().to_dict()
