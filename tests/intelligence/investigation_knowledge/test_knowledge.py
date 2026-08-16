from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.investigation_knowledge import InvestigationKnowledgeService
from services.intelligence.investigation_knowledge.models import KnowledgeEvolution
from services.intelligence.investigation_knowledge.evolution_analysis import EvolutionAnalysis
def test_knowledge_boundaries():
    with pytest.raises(FrozenInstanceError): KnowledgeEvolution("i","t").maturity="advanced"
    assert InvestigationKnowledgeService().derive("a")["knowledge_id"]!=InvestigationKnowledgeService().derive("b")["knowledge_id"]
    assert "evidence indicates" in EvolutionAnalysis().analyze({"history":[1]})["trends"][0]
