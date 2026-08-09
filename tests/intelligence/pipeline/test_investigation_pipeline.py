"""
Investigation Pipeline Tests

Validates end-to-end intelligence
pipeline execution flow.
"""

from importlib import import_module


try:
    InvestigationPipeline = import_module(
        "services.intelligence.pipeline"
    ).InvestigationPipeline
except ModuleNotFoundError:
    InvestigationPipeline = import_module(
        "src.services.intelligence.pipeline"
    ).InvestigationPipeline


class FakeAnalyzer:
    """
    Fake investigation analyzer.
    """

    def analyze(self, artifacts):
        return {
            "status": "completed",
            "artifacts": artifacts,
            "risk": "high",
        }


class FakeOrchestrator:
    """
    Fake investigation orchestrator.
    """

    def execute(self, context):
        return {
            "execution": "completed",
            "context": context,
        }


def create_pipeline():
    return InvestigationPipeline(
        analyzer=FakeAnalyzer(),
        orchestrator=FakeOrchestrator(),
    )


def test_pipeline_initialization():

    pipeline = create_pipeline()

    assert pipeline is not None


def test_pipeline_execution():

    pipeline = create_pipeline()

    result = pipeline.run(
        [
            {
                "type": "ioc",
                "value": "evil-domain.xyz",
            }
        ]
    )

    assert result["status"] == "completed"


def test_pipeline_contains_analysis():

    pipeline = create_pipeline()

    result = pipeline.run(
        [
            {
                "type": "threat",
                "value": "phishing",
            }
        ]
    )

    assert "analysis" in result


def test_pipeline_contains_execution():

    pipeline = create_pipeline()

    result = pipeline.run(
        [
            {
                "type": "ioc",
                "value": "10.10.10.10",
            }
        ]
    )

    assert "execution" in result


def test_pipeline_empty_input():

    pipeline = create_pipeline()

    result = pipeline.run([])

    assert result["status"] == "completed"