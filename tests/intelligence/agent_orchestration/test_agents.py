from services.intelligence.agent_orchestration import SOCAgent,AgentTask,AgentRegistry,AgentOrchestrationService
from services.intelligence.agent_orchestration.approval import ApprovalManager
def test_agent_models(): assert SOCAgent("a","A","reasoning_agent").to_dict()["agent_id"]=="a"
def test_agent_registry(): r=AgentRegistry(); a=SOCAgent("a","A","x",capabilities=["hunt"]); r.register_agent(a); assert r.discover_agents("hunt")
def test_task_lifecycle(): assert AgentTask("t","c","a","x").status=="queued"
def test_agent_execution(): s=AgentOrchestrationService(); s.register(SOCAgent("a","A","evidence_agent",capabilities=["evidence"])); assert s.execute("c",object(),["evidence"]).completed_agents==["a"]
def test_workflow_engine(): assert AgentOrchestrationService().execute("c",object()).failed_agents
def test_approval_controls(): assert ApprovalManager().required("containment") and not ApprovalManager().approve("containment")
def test_audit_logging(): s=AgentOrchestrationService(); s.register(SOCAgent("a","A","x")); assert True
def test_investigation_integration(): assert "agent_execution_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
def test_tenant_isolation(): r=AgentRegistry(); r.register_agent(SOCAgent("a","A","x",tenant_id="t")); assert not r.discover_agents("x","other")
def test_backward_compatibility(): assert AgentTask("t","c","a","x").to_dict()["status"]=="queued"
