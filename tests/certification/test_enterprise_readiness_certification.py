import pytest

from services.intelligence.certification import (
    CertificationReportGenerator,
    EnterpriseCertificationRunner,
)


EXPECTED_SOURCES = {
    "investigation_memory",
    "organizational_cyber_memory",
    "operational_accuracy",
    "enterprise_proof",
    "controlled_operational_pilot",
    "performance_telemetry",
    "billing_entitlement_validation",
}


def _report():
    return EnterpriseCertificationRunner(
        generated_at="2026-08-25T00:00:00+00:00",
        commit_sha="synthetic-commit-sha",
    ).run()


def test_certification_aggregates_all_required_evidence_sources():
    report = _report()

    assert {item.source for item in report.evidence} == EXPECTED_SOURCES
    assert all(item.status == "passed" for item in report.evidence)
    assert all(item.source_replay_digest for item in report.evidence)
    assert all(item.source_report_digest for item in report.evidence if item.source != "performance_telemetry")
    assert all(item.evidence_digest for item in report.evidence)
    assert len(report.evidence_references) == 7


def test_certification_controls_cover_security_ai_performance_and_operations():
    report = _report()
    control_ids = {item.control_id for item in report.controls}

    assert len(report.controls) == 22
    assert report.failed_controls == ()
    assert set(report.passed_controls) == control_ids
    assert {
        "SEC-TENANT-ISOLATION",
        "SEC-AUTHORIZATION",
        "SEC-FAIL-CLOSED",
        "SEC-AUDIT-INTEGRITY",
        "SEC-APPEND-ONLY",
        "AI-VERDICT-CONSISTENCY",
        "AI-EVIDENCE-PROVENANCE",
        "AI-CONFIDENCE-CALIBRATION",
        "AI-MEMORY-ADVISORY",
        "PERF-LATENCY",
        "PERF-SCALE",
        "PERF-MEMORY-OVERHEAD",
        "OPS-REPLAY-STABILITY",
        "OPS-DETERMINISTIC-EXECUTION",
        "OPS-REPORT-INTEGRITY",
        "BILLING-UNPAID-SAFETY",
        "BILLING-ENTITLEMENT-TRANSITION",
        "BILLING-UPGRADE-PRESERVATION",
        "BILLING-DOWNGRADE-SAFETY",
        "BILLING-INVESTIGATION-PRESERVATION",
        "BILLING-FAILURE-FAIL-CLOSED",
        "BILLING-AUDIT-CONTINUITY",
    } == control_ids


def test_certification_consumes_billing_scenarios_and_security_invariants():
    report = _report()
    evidence = next(item for item in report.evidence if item.source == "billing_entitlement_validation")

    assert evidence.summary["metrics"]["scenario_count"] == 5
    assert all(evidence.summary["security_invariants"].values())
    assert {item.control_id for item in report.controls if item.domain == "billing"} == {
        "BILLING-UNPAID-SAFETY",
        "BILLING-ENTITLEMENT-TRANSITION",
        "BILLING-UPGRADE-PRESERVATION",
        "BILLING-DOWNGRADE-SAFETY",
        "BILLING-INVESTIGATION-PRESERVATION",
        "BILLING-FAILURE-FAIL-CLOSED",
        "BILLING-AUDIT-CONTINUITY",
    }


def test_certification_metrics_and_findings_are_auditable():
    report = _report()
    metric_names = {item.name for item in report.metrics}

    assert "Organizational verdict agreement" in metric_names
    assert "Confidence calibration" in metric_names
    assert "Memory benefit score" in metric_names
    assert "Pilot p50 investigation latency" in metric_names
    assert "Pilot p95 investigation latency" in metric_names
    assert "1000-investigation memory overhead" in metric_names
    assert report.findings
    assert any(item.status == "passed" for item in report.findings)
    assert report.warnings
    assert report.validation_digest
    assert report.report_digest
    assert report.immutable is True


def test_certification_replay_digest_is_stable_and_commit_metadata_is_preserved():
    first = _report()
    second = _report()

    runner = EnterpriseCertificationRunner(commit_sha="synthetic-commit-sha")
    assert runner.verify_replay(first, second)
    assert first.replay_digest == second.replay_digest
    assert first.commit_sha == "synthetic-commit-sha"
    assert first.environment_metadata["external_integrations"] is False
    assert first.environment_metadata["production_deployment"] is False


def test_certification_report_write_is_append_only(tmp_path):
    report = _report()
    target = tmp_path / "enterprise-certification.json"

    assert CertificationReportGenerator.write(report, target) == target
    with pytest.raises(FileExistsError, match="immutable_certification_report_exists"):
        CertificationReportGenerator.write(report, target)
