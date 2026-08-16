from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.investigation_workflow import InvestigationWorkflowService
from services.intelligence.investigation_workflow.models import WorkflowInsight
def test_workflow_is_frozen_and_history_aware():
    with pytest.raises(FrozenInstanceError): WorkflowInsight("i","t").tenant_id="x"
    assert InvestigationWorkflowService().derive("t")["confidence"]=="insufficient_history"
