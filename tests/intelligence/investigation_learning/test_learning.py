from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.investigation_learning import InvestigationLearningService
from services.intelligence.investigation_learning.models import LearningInsight
from services.intelligence.investigation_learning.pattern_analysis import PatternAnalysis
def test_frozen_deterministic_and_insufficient_history():
    with pytest.raises(FrozenInstanceError): LearningInsight("i","t").tenant_id="x"
    a=InvestigationLearningService().derive("a"); b=InvestigationLearningService().derive("b")
    assert a["learning_id"]!=b["learning_id"] and a["confidence"]=="insufficient_history" and a["advisory_only"]
    assert PatternAnalysis().analyze({})["patterns"]==()
