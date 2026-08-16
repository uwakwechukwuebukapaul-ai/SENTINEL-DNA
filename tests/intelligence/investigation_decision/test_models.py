from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.investigation_decision.models import DecisionAnalysis


def test_decision_model_is_frozen():
    with pytest.raises(FrozenInstanceError):
        DecisionAnalysis("tenant", "analysis").decision_posture = "ready"
