from services.intelligence.correlation import CorrelationService, CorrelationRepository, SecuritySignal
from services.intelligence.investigation.investigation_result import InvestigationResult

def signals(tenant="a"):
    return [SecuritySignal("1", tenant, "failed_login"), SecuritySignal("2", tenant, "authentication_failure")]

def test_correlation_accuracy():
    result = CorrelationService("a").correlate(signals())
    assert "brute-force" in result.matched_rules and result.confidence >= .75

def test_tenant_isolation():
    service = CorrelationService("a", CorrelationRepository())
    result = service.correlate(signals("b"))
    assert result.signals == [] and service.repository.list_signals("b") == []

def test_false_positive_handling():
    result = CorrelationService("a").correlate([SecuritySignal("1", "a", "heartbeat")])
    assert result.false_positive is True and CorrelationService("a").create_trigger(result) is None

def test_trigger_generation_requires_approval():
    service = CorrelationService("a")
    trigger = service.create_trigger(service.correlate(signals()))
    assert trigger is not None and trigger.requires_human_approval is True and trigger.status == "pending"

def test_backward_compatibility():
    result = InvestigationResult()
    assert result.correlation_context is None and "correlation_context" in result.to_dict()
