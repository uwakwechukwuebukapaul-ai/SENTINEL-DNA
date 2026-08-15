from services.intelligence.workspace import AnalystWorkspaceService, WorkspaceRepository
def row(tenant): return {"tenant_id":tenant,"investigation_id":"i1","case_id":"c1","status":"open","confidence":.7,"timeline":[{"timestamp":"2024-01-02","event_type":"finding"}],"evidence":[{"id":"e1","provenance":{"source":"evidence-engine"}}],"decisions":[{"priority":"high","source_subsystem":"governance","rationale":"review","confidence":.8}]}
def test_workspace_context_flow_and_provenance():
    s=AnalystWorkspaceService(WorkspaceRepository([row("a")]),"a"); context=s.get_workspace("i1"); assert context.state=="partial" and context.timeline[0]["event_type"]=="finding" and s.get_decision_surface("i1")[0]["requires_human_review"] and s.get_provenance("i1")
def test_tenant_isolation_and_insufficient_evidence():
    s=AnalystWorkspaceService(WorkspaceRepository([row("a"),row("b")]),"a"); assert s.get_workspace("i1").tenant_id=="a"; empty=AnalystWorkspaceService(WorkspaceRepository([{"tenant_id":"a","investigation_id":"empty"}]),"a").get_evidence_view("empty"); assert empty["status"]=="insufficient" and empty["requires_human_review"]
def test_partial_source_state_and_no_mutation():
    source=row("a"); before=dict(source); context=AnalystWorkspaceService(WorkspaceRepository([source]),"a").get_workspace("i1",compliance=None,quality=None); assert context.state=="partial" and source==before and context.copilot["advisory"]
