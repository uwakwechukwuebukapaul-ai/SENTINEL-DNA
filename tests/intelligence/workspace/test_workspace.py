from services.intelligence.workspace import SOCWorkspaceAggregator, SOCWorkspaceService, WorkspaceRepository
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_workspace_aggregation_and_partial_availability():
    snapshot = SOCWorkspaceAggregator().snapshot("inv-1", "case-1", {"status": "active", "summary": "triage"})
    assert snapshot.investigation_id == "inv-1" and snapshot.availability == "partial" and snapshot.soar_summary is None

def test_workspace_serialization():
    data = SOCWorkspaceAggregator().snapshot("inv-1").to_dict()
    assert data["investigation_id"] == "inv-1" and "created_at" in data

def test_tenant_isolation():
    service = SOCWorkspaceService(WorkspaceRepository([{"case_id": "c1", "tenant_id": "a"}]), tenant_id="b")
    assert service.get_case_workspace("c1") is None

def test_empty_investigation():
    assert SOCWorkspaceService().get_investigation_workspace("missing") is None

def test_investigation_result_compatibility():
    result = InvestigationResult()
    assert result.workspace_context is None and "workspace_context" in result.to_dict()
