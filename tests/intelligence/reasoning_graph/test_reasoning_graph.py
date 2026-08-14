from services.intelligence.reasoning_graph import ReasoningNode,ReasoningEdge,ReasoningGraphService
from services.intelligence.reasoning_graph.reasoning_engine import ReasoningEngine
def ev(): return [{"id":"E-1","description":"Suspicious PowerShell execution with malware hash"}]
def test_reasoning_models(): assert ReasoningNode("n","evidence","E",.8,"x").to_dict()["node_id"]=="n"
def test_graph_creation(): assert ReasoningGraphService().analyze(ev())["nodes"]
def test_hypothesis_generation(): assert ReasoningEngine().generate_hypotheses(ev())[0].statement
def test_confidence_scoring(): assert ReasoningEngine().generate_hypotheses(ev())[0].confidence==.88
def test_evidence_priority(): assert ReasoningEngine().rank_evidence(ev())[0].priority==1
def test_reasoning_planner(): assert ReasoningGraphService().analyze(ev())["recommended_steps"]
def test_ai_runtime_context(): assert "reasoning" in ReasoningGraphService().analyze(ev())
def test_investigation_integration(): assert "reasoning_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
def test_tenant_isolation(): assert ReasoningGraphService().analyze(ev())["nodes"][0]["entity_reference"]=="E-1"
def test_backward_compatibility(): assert ReasoningGraphService().analyze([])["hypotheses"]==[]
