"""
Runtime Intelligence Metrics Tests
"""

from services.intelligence.runtime.runtime_intelligence_metrics import (
    RuntimeIntelligenceMetrics,
)



def test_metrics_execution_tracking():

    metrics = RuntimeIntelligenceMetrics()


    metrics.record_execution(
        True
    )

    metrics.record_execution(
        False
    )


    result = metrics.summary()


    assert (
        result["executions"]
        ==
        2
    )


    assert (
        result["successful"]
        ==
        1
    )


    assert (
        result["failed"]
        ==
        1
    )



def test_confidence_tracking():

    metrics = RuntimeIntelligenceMetrics()


    metrics.record_confidence(
        0.8
    )


    metrics.record_confidence(
        1.0
    )


    result = metrics.summary()


    assert (
        result["average_confidence"]
        ==
        0.9
    )