from services.intelligence.adaptive_workflow import AdaptiveWorkflowService,AdaptiveWorkflowRouter
def test_state_machine():
 s=AdaptiveWorkflowService(); c=s.recommend("c"); assert s.transition(c,"TRIAGING").state=="TRIAGING"
def test_workflow_routing(): assert AdaptiveWorkflowRouter().recommend(threat_type="phishing")["agents"][-1]=="reporting_agent"
def test_branching_logic(): assert "hunting_agent" in AdaptiveWorkflowRouter().recommend(threat_type="ransomware")["agents"]
def test_risk_prioritization(): assert AdaptiveWorkflowRouter().recommend(severity="critical")["priority"]=="high"
def test_governance_controls(): assert AdaptiveWorkflowRouter().recommend(threat_type="ransomware")["approval_required"] is False
def test_backward_compatibility(): assert "adaptive_workflow_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
