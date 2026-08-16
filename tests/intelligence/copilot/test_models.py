from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.copilot.models import CopilotContext
def test_context_model_is_frozen_and_tenant_scoped():
    value=CopilotContext('tenant','case');assert value.tenant_id=='tenant'
    with pytest.raises(FrozenInstanceError):value.case_id='other'
