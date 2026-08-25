import pytest

from services.intelligence.pilot import (
    OperationalPilotReportGenerator,
    OperationalPilotRunner,
    default_pilot_alerts,
)


def test_default_pilot_covers_tenants_a_b_c_and_controlled_failure():
    alerts = default_pilot_alerts()
    assert {item.tenant_id for item in alerts} == {
        "tenant-pilot-a",
        "tenant-pilot-b",
        "tenant-pilot-c",
    }
    assert sum(item.failure_mode is not None for item in alerts) == 1


def test_pilot_reports_required_operational_metrics():
    report = OperationalPilotRunner(generated_at="2026-08-25T00:00:00+00:00").run()
    metrics = report.metrics

    assert metrics.investigations_completed == 4
    assert metrics.successful_investigations == 3
    assert metrics.failed_investigations == 1
    assert metrics.mean_investigation_latency_ms > 0
    assert metrics.p50_investigation_latency_ms <= metrics.p95_investigation_latency_ms
    assert metrics.evidence_retrieval_timing_ms > 0
    assert metrics.ioc_enrichment_timing_ms > 0
    assert metrics.mitre_mapping_timing_ms > 0
    assert metrics.memory_retrieval_timing_ms > 0
    assert metrics.report_generation_timing_ms > 0
    assert metrics.investigation_memory_items > 0
    assert metrics.organizational_memory_items > 0
    assert metrics.analyst_feedback_captured == 3


def test_pilot_memory_improves_context_and_preserves_provenance():
    report = OperationalPilotRunner(generated_at="2026-08-25T00:00:00+00:00").run()
    successful = [item for item in report.executions if item.successful]

    assert any(item.memory_context_improved for item in successful)
    assert all(item.investigation_memory_items > 0 for item in successful)
    assert all(item.organizational_memory_items > 0 for item in successful)
    assert all(item.feedback is not None for item in successful)
    assert all(item.evidence for item in successful)
    assert all(item.audit_hash for item in report.executions)
    assert all(OperationalPilotRunner._chain_valid(item.provenance_chain) for item in report.executions)
    assert OperationalPilotRunner._chain_valid(report.provenance_chain)


def test_pilot_failed_execution_remains_fail_closed():
    report = OperationalPilotRunner(generated_at="2026-08-25T00:00:00+00:00").run()
    failed = [item for item in report.executions if not item.successful]

    assert len(failed) == 1
    assert failed[0].failure_reason == "synthetic_evidence_provider_timeout"
    assert failed[0].enforced_verdict is None
    assert failed[0].fail_closed is True
    assert failed[0].authorization_status == failed[0].alert.authorization_status


def test_pilot_safety_invariants_and_result_contract_are_unchanged():
    report = OperationalPilotRunner(generated_at="2026-08-25T00:00:00+00:00").run()

    assert all(report.safety_validation.values())
    assert report.safety_validation["authorization_unchanged"] is True
    assert report.safety_validation["tenant_isolation_unchanged"] is True
    assert report.safety_validation["no_tenant_leakage"] is True
    assert report.safety_validation["fail_closed_behavior_unchanged"] is True
    assert report.safety_validation["memory_advisory_only"] is True
    assert report.safety_validation["verdict_enforcement_unchanged"] is True
    assert report.safety_validation["investigation_result_contract_unchanged"] is True
    assert report.safety_validation["no_autonomous_response_actions"] is True


def test_pilot_replay_digest_is_identical_across_runs():
    first_runner = OperationalPilotRunner(generated_at="2026-08-25T00:00:00+00:00")
    second_runner = OperationalPilotRunner(generated_at="2026-08-25T00:00:00+00:00")
    first = first_runner.run()
    second = second_runner.run()

    assert first_runner.verify_replay(first, second)
    assert first.replay_digest == second.replay_digest
    assert first.report_digest == second.report_digest


def test_pilot_report_write_is_append_only(tmp_path):
    report = OperationalPilotRunner(generated_at="2026-08-25T00:00:00+00:00").run()
    target = tmp_path / "operational-pilot.json"

    assert OperationalPilotReportGenerator.write(report, target) == target
    with pytest.raises(FileExistsError, match="immutable_operational_pilot_exists"):
        OperationalPilotReportGenerator.write(report, target)
