from services.incidents.workflow.service import WorkflowService
from services.incidents.collaboration.service import CollaborationService
from services.incidents.sla.calculator import SLACalculator
def test_workflow_valid_transition_and_history():
    service = WorkflowService(); service.create("inc-1", "org-a"); item = service.transition("inc-1", "org-a", "TRIAGED", 1, "acknowledged"); assert item.history[0]["new_state"] == "TRIAGED"
def test_invalid_transition_rejected():
    service = WorkflowService(); service.create("inc-1", "org-a")
    try: service.transition("inc-1", "org-a", "RESOLVED", 1)
    except ValueError: return
    assert False
def test_collaboration_tenant_isolation():
    service = CollaborationService(); service.comment("inc-1", "org-a", 1, "note"); assert service.list_comments("inc-1", "org-b") == []
def test_sla_calculator():
    timestamps = {"NEW": "2026-08-14T10:00:00+00:00", "TRIAGED": "2026-08-14T10:02:00+00:00", "INVESTIGATING": "2026-08-14T10:04:00+00:00", "RESOLVED": "2026-08-14T10:20:00+00:00"}; assert SLACalculator().calculate(timestamps)["MTTR"] == 1200
