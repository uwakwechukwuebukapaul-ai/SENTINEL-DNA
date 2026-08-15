from services.automation_governance import *
from services.automation_governance.models import ActionType, RiskLevel
def test_approval_and_simulation():
    s=AutomationGovernanceService(); w=s.create_workflow("t1","containment"); a=AutomationAction("a",w.workflow_id,ActionType.ISOLATE_SIMULATION,"edr",RiskLevel.HIGH); s.add_action("t1",a); e,ap=s.request_execution("t1",w.workflow_id,"analyst"); assert e.status=="PENDING_APPROVAL"; out=s.approve_and_execute("t1",e.execution_id,ap.approval_id,"manager"); assert out.status=="SUCCESS" and out.result["simulation"]
def test_tenant_isolation_and_rejection():
    s=AutomationGovernanceService(); w=s.create_workflow("t1","x"); assert s.repository.get_workflow(w.workflow_id,"t2") is None
    try: s.add_action("t1",AutomationAction("a",w.workflow_id,"DELETE","x"))
    except PermissionError: pass
    else: assert False
