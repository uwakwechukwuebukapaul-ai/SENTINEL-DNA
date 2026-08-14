from services.intelligence.ai_runtime import AIRuntimeService, DeterministicMockProvider
from services.intelligence.orchestration.investigation_coordinator import InvestigationContext
from services.intelligence.orchestration.investigation_orchestrator import InvestigationOrchestrator


class CountingInvestigator:
    calls = 0

    def investigate(self, case_id, artifacts):
        self.calls += 1
        return {"case_id": case_id, "analysis": {"risk": "low"}}


class CountingExecution:
    calls = 0

    def execute(self, investigation):
        self.calls += 1
        return {"status": "completed", "action": "none"}


def _orchestrator(ai_runtime=None):
    return InvestigationOrchestrator(
        investigator=CountingInvestigator(),
        execution_engine=CountingExecution(),
        ai_runtime=ai_runtime,
    )


def test_mock_provider_is_deterministic_and_offline():
    provider = DeterministicMockProvider()
    first = provider.generate("prompt", {"case_id": "CASE-1"})
    second = provider.generate("prompt", {"case_id": "CASE-1"})
    assert first == second
    assert first.metadata["offline_only"] is True
    assert first.metadata["synthetic"] is True


def test_orchestrator_works_without_ai_provider():
    result = _orchestrator().investigate("CASE-1", artifacts=[{"type": "alert"}])
    assert result["success"] is True
    assert result["ai_reasoning"] is None


def test_orchestrator_adds_ai_metadata_without_duplicate_execution():
    investigator = CountingInvestigator()
    execution = CountingExecution()
    orchestrator = InvestigationOrchestrator(
        investigator=investigator,
        execution_engine=execution,
        ai_runtime=AIRuntimeService(DeterministicMockProvider()),
    )
    context = InvestigationContext("INV-CASE-1", evidence=[{"id": "E-1"}])
    result = orchestrator.investigate(
        "CASE-1",
        artifacts=[{"type": "alert"}],
        context=context,
    )
    assert result["success"] is True
    assert result["ai_reasoning"]
    assert result["ai_confidence"] == 0.75
    assert result["ai_evidence_references"] == ["E-1"]
    assert result["ai_provider"] == "deterministic_mock"
    assert investigator.calls == 1
    assert execution.calls == 1
