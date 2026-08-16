from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.investigation_lifecycle.models import LifecycleIntelligence
def test_lifecycle_model_is_frozen():
    with pytest.raises(FrozenInstanceError): LifecycleIntelligence('t','c','i').current_lifecycle_stage='analysis'
