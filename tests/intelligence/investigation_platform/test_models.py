from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.investigation_platform.models import InvestigationIntelligence
def test_investigation_model_is_frozen():
    with pytest.raises(FrozenInstanceError): InvestigationIntelligence('t','c','i').investigation_posture='ready'
