from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.hunting_platform.models import HuntingIntelligence
def test_hunting_model_is_frozen():
    with pytest.raises(FrozenInstanceError): HuntingIntelligence('t','i').current_hunting_posture='available'
