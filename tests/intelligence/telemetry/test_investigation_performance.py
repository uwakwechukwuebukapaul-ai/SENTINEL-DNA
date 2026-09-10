from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.orchestration.investigation_coordinator import InvestigationCoordinator
from services.intelligence.telemetry import (
    COMPONENTS,
    InvestigationPerformanceTelemetry,
    run_performance_benchmark,
)


class RecordingAudit:
    def __init__(self):
        self.events = []

    def record(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))
        return "AUDIT-TELEMETRY-1"


def test_trace_captures_all_components_and_appends_tenant_audit_evidence():
    audit = RecordingAudit()
    trace = InvestigationPerformanceTelemetry(audit).start_trace(
        case_id="CASE-TELEMETRY-1",
        tenant_id="tenant-a",
        investigation_id="INV-TELEMETRY-1",
    )
    for component in COMPONENTS[1:]:
        trace.begin_stage(component)
        trace.end_stage(component)

    summary = trace.finish(status="completed")

    assert summary["tenant_scoped"] is True
    assert summary["append_only_audit"] is True
    assert summary["audit_status"] == "persisted"
    assert summary["audit_event_id"] == "AUDIT-TELEMETRY-1"
    assert set(summary["components"]) == set(COMPONENTS)
    assert summary["components"]["coordinator"]["is_end_to_end_envelope"] is True
    assert audit.events[0][0] == "investigation_performance_telemetry"
    assert audit.events[0][1]["tenant_id"] == "tenant-a"


def test_trace_requires_tenant_for_persisted_evidence_without_affecting_execution():
    audit = RecordingAudit()
    trace = InvestigationPerformanceTelemetry(audit).start_trace(
        case_id="CASE-TELEMETRY-2", tenant_id=None
    )

    summary = trace.finish(status="completed")

    assert summary["audit_status"] == "not_persisted_tenant_required"
    assert audit.events == []
    assert summary["authorization_impact"] == "none"
    assert summary["decision_impact"] == "none"


def test_coordinator_contract_and_result_schema_are_preserved():
    coordinator = InvestigationCoordinator()
    result = coordinator.investigate(
        "CASE-TELEMETRY-3",
        {"kind": "synthetic-alert"},
        tenant_id="tenant-telemetry-tests",
    )

    assert isinstance(result, InvestigationResult)
    assert set(result.to_dict()) == set(InvestigationResult().to_dict())
    assert result.metadata["performance_telemetry"]["tenant_id"] == "tenant-telemetry-tests"
    assert result.metadata["performance_telemetry"]["authorization_impact"] == "none"
    assert result.metadata["performance_telemetry"]["decision_impact"] == "none"
    assert result.metadata["performance_telemetry"]["audit_status"] == "persisted"
    events = coordinator.audit_service.list_for_tenant(
        "tenant-telemetry-tests", event_type="investigation_performance_telemetry"
    )
    assert events
    assert events[0]["resource_type"] == "investigation"


def test_benchmark_report_has_all_components_and_replay_evidence():
    first = run_performance_benchmark(
        iterations=3,
        synthetic_stage_delay_ms=0,
        generated_at="2026-08-25T00:00:00+00:00",
    )
    second = run_performance_benchmark(
        iterations=3,
        synthetic_stage_delay_ms=0,
        generated_at="2026-08-25T00:00:00+00:00",
    )

    assert first.iterations == 3
    assert set(first.component_statistics) == set(COMPONENTS)
    assert all(first.control_checks.values())
    assert first.deterministic_replay["input_digest"] == second.deterministic_replay["input_digest"]
    assert first.deterministic_replay["timings_excluded"] is True
