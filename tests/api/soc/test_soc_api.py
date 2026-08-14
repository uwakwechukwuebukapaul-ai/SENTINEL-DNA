from services.api.soc.service import SOCAPIService
from services.api.soc.schemas import SOCResponse
from services.intelligence.soc_workspace import SOCWorkspaceService

def service(): return SOCAPIService(SOCWorkspaceService(cases=[{"case_id":"C-1","status":"completed","risk":{"severity":"high"},"confidence":.9}]))
def test_dashboard_endpoint(): assert service().get_dashboard()[0].active_cases == 1
def test_case_endpoint(): assert service().get_case_view("C-1")[0].case_id == "C-1"
def test_threat_posture_endpoint(): assert service().get_threat_posture()[0].total_cases == 1
def test_metrics_endpoint(): assert service().get_metrics()[0]["volume"]["total"] == 1
def test_partial_failure_response(): assert SOCAPIService(type("Broken",(),{"get_dashboard":lambda s: (_ for _ in ()).throw(RuntimeError())})()).get_dashboard()[0] is None
def test_serialization(): assert SOCResponse(data=service().get_dashboard()[0]).to_dict()["success"]
