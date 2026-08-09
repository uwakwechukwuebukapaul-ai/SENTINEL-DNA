"""
Sentinel DNA Investigation Orchestrator Tests

Validates:

- orchestrator lifecycle
- investigation execution
- correlation integration
- fusion integration
- reasoning integration
- result normalization
- execution history
- failure handling
"""

from services.intelligence.investigation.investigation_orchestrator import (
    InvestigationOrchestrator,
)


class FakeCorrelationResult:
    def __init__(self):
        self.matched = True
        self.risk = "high"
        self.confidence = 0.85
        self.entities = ["evil.com"]
        self.relationships = []
        self.mitre = ["T1566"]
        self.attack_pattern = "credential_phishing"

    def to_dict(self):
        return {
            "matched": self.matched,
            "risk": self.risk,
            "confidence": self.confidence,
            "entities": self.entities,
            "relationships": self.relationships,
            "mitre": self.mitre,
            "attack_pattern": self.attack_pattern,
        }


class FakeCorrelationEngine:
    def correlate(self, signals):
        assert len(signals) == 2

        return FakeCorrelationResult()


class FakeFusionEngine:
    def fuse(self, payload):
        return {
            "threat_assessment": {
                "risk": "critical",
                "confidence": 0.95,
            },
            "summary": "Critical phishing activity detected.",
            "recommendations": [
                "Contain affected host.",
            ],
            "mitre": ["T1566"],
        }


class FakeReasoningEngine:
    def reason(
        self,
        artifacts=None,
        correlation=None,
        fusion=None,
        context=None,
    ):
        return {
            "conclusion": "Malicious phishing activity.",
        }


def create_orchestrator():
    return InvestigationOrchestrator(
        correlation_engine=FakeCorrelationEngine(),
        fusion_engine=FakeFusionEngine(),
        reasoning_engine=FakeReasoningEngine(),
    )


def test_orchestrator_creation():
    orchestrator = create_orchestrator()

    assert orchestrator is not None
    assert orchestrator.running is False


def test_start():
    orchestrator = create_orchestrator()

    assert orchestrator.start() is True
    assert orchestrator.running is True


def test_stop():
    orchestrator = create_orchestrator()

    orchestrator.start()

    assert orchestrator.stop() is True
    assert orchestrator.running is False


def test_execute_investigation():
    orchestrator = create_orchestrator()

    result = orchestrator.investigate(
        artifacts=[
            {
                "type": "domain",
                "value": "evil.com",
            },
            {
                "type": "email",
                "value": "phishing",
            },
        ],
        case_id="CASE-001",
    )

    assert result.success is True
    assert result.status == "completed"
    assert result.case_id == "CASE-001"
    assert result.investigation_id is not None


def test_correlation_result():
    orchestrator = create_orchestrator()

    result = orchestrator.investigate(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    assert result.success is True
    assert result.correlation["risk"] == "high"


def test_fusion_result():
    orchestrator = create_orchestrator()

    result = orchestrator.investigate(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    assert result.fusion["threat_assessment"]["risk"] == "critical"
    assert result.risk == "critical"


def test_reasoning_result():
    orchestrator = create_orchestrator()

    result = orchestrator.investigate(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    assert result.reasoning["reasoning_status"] == "completed"
    assert result.reasoning["reasoning_available"] is True


def test_execution_history():
    orchestrator = create_orchestrator()

    orchestrator.investigate(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    orchestrator.investigate(
        [
            {
                "type": "domain",
                "value": "malicious.example",
            },
        ]
    )

    history = orchestrator.get_execution_history()

    assert len(history) == 2


def test_clear_execution_history():
    orchestrator = create_orchestrator()

    orchestrator.investigate(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    assert len(
        orchestrator.get_execution_history()
    ) == 1

    assert orchestrator.clear_execution_history() is True

    assert (
        orchestrator.get_execution_history()
        == []
    )

    assert orchestrator.last_result is None


def test_failure_result():
    class BrokenCorrelation:
        def correlate(self, signals):
            raise RuntimeError(
                "correlation failure"
            )

    orchestrator = InvestigationOrchestrator(
        correlation_engine=BrokenCorrelation(),
        fusion_engine=FakeFusionEngine(),
    )

    result = orchestrator.investigate(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    assert result.success is False
    assert result.status == "failed"
    assert "correlation failure" in result.error


def test_empty_artifacts():
    orchestrator = create_orchestrator()

    result = orchestrator.investigate([])

    assert result.success is True
    assert result.status == "completed"


def test_execute_alias():
    orchestrator = create_orchestrator()

    result = orchestrator.execute(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    assert result.success is True


def test_run_alias():
    orchestrator = create_orchestrator()

    result = orchestrator.run(
        [
            {
                "type": "domain",
                "value": "evil.com",
            },
        ]
    )

    assert result.success is True